from nautobot.apps.jobs import (
    Job,
    StringVar,
    BooleanVar,
    IPNetworkVar,
    IPAddressWithMaskVar,
    ObjectVar,
    register_jobs,
)
from nautobot.dcim.models import Location, Device, Interface, DeviceType, DeviceRole
from nautobot.ipam.models import Prefix, IPAddress
from nautobot.extras.models import Status
from django.core.exceptions import ValidationError

class GenerateRecords(Job):
    """Generate Location, Device, Interface, Prefix & IP Address."""

    class Meta:
        name = "Generate Records"
        description = "Generate various Nautobot records"
        has_sensitive_variables = False

    location_name = StringVar(required=True, description="Name of the Location")
    device_name   = StringVar(required=True, description="Name of the Device")
    device_type   = ObjectVar(model=DeviceType,    required=True, description="Device Type")
    device_role   = ObjectVar(model=DeviceRole,    required=True, description="Device Role")
    interface_name = StringVar(required=True, description="Name of the Interface")
    ip_prefix     = IPNetworkVar(required=True, description="IP prefix (e.g. 192.168.1.0/24)")
    ip_address    = IPAddressWithMaskVar(required=True, description="IP addr (e.g. 192.168.1.1/24)")

    def run(self, data, commit):
        try:
            # Location
            loc = Location(name=data["location_name"], status=Status.objects.get(name="Active"))
            loc.validated_save()
            self.log_success(f"Location created: {loc}")

            # Device
            dev = Device(
                name=data["device_name"],
                device_type=data["device_type"],
                device_role=data["device_role"],
                location=loc,
                status=Status.objects.get(name="Active"),
            )
            dev.validated_save()
            self.log_success(f"Device created: {dev}")

            # Interface
            iface = Interface(
                name=data["interface_name"],
                device=dev,
                status=Status.objects.get(name="Active"),
                type="1000base-t",
            )
            iface.validated_save()
            self.log_success(f"Interface created: {iface}")

            # Prefix
            pref = Prefix(prefix=data["ip_prefix"], status=Status.objects.get(name="Active"))
            pref.validated_save()
            self.log_success(f"Prefix created: {pref}")

            # IP Address
            ip = IPAddress(
                address=data["ip_address"],
                status=Status.objects.get(name="Active"),
                assigned_object=iface,
            )
            ip.validated_save()
            self.log_success(f"IP Address created: {ip}")

            return f"All records for {data['device_name']} created successfully."
        except ValidationError as e:
            self.log_failure(f"Validation error: {e}")
            return f"Validation failed: {e}"
        except Exception as e:
            self.log_failure(f"Unexpected error: {e}")
            return f"Error: {e}"

register_jobs(GenerateRecords)
