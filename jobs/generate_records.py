from nautobot.extras.jobs import Job, StringVar, BooleanVar
from nautobot.dcim.models import Location, Device, Interface
from nautobot.ipam.models import IPAddress, Prefix
from nautobot.extras.models import Status
from nautobot.core.utils.lookup import get_route_for_model
from django.core.exceptions import ValidationError
import ipaddress

class GenerateRecords(Job):
    """
    Job to generate various Nautobot records including locations, devices, interfaces, DNS records, IP Prefixes, and IP addresses.
    """
    class Meta:
        name = "Generate Records"
        description = "Generate various Nautobot records"
        has_sensitive_variables = False

    # Job variables
    location_name = StringVar(
        description="Name of the location to create",
        required=True,
    )
    device_name = StringVar(
        description="Name of the device to create",
        required=True,
    )
    interface_name = StringVar(
        description="Name of the interface to create",
        required=True,
    )
    ip_prefix = StringVar(
        description="IP Prefix to create (e.g., 192.168.1.0/24)",
        required=True,
    )
    ip_address = StringVar(
        description="IP Address to create (e.g., 192.168.1.1/24)",
        required=True,
    )

    def run(self, data, commit):
        """
        Main job execution method.
        """
        try:
            # Create Location
            self.log_info("Creating location...")
            location = Location(
                name=data["location_name"],
                status=Status.objects.get(name="Active"),
            )
            location.validated_save()
            self.log_success(f"Created location: {location.name}")

            # Create Device
            self.log_info("Creating device...")
            device = Device(
                name=data["device_name"],
                location=location,
                status=Status.objects.get(name="Active"),
            )
            device.validated_save()
            self.log_success(f"Created device: {device.name}")

            # Create Interface
            self.log_info("Creating interface...")
            interface = Interface(
                name=data["interface_name"],
                device=device,
                status=Status.objects.get(name="Active"),
                type="1000base-t",
            )
            interface.validated_save()
            self.log_success(f"Created interface: {interface.name}")

            # Create IP Prefix
            self.log_info("Creating IP prefix...")
            prefix = Prefix(
                prefix=data["ip_prefix"],
                status=Status.objects.get(name="Active"),
            )
            prefix.validated_save()
            self.log_success(f"Created prefix: {prefix.prefix}")

            # Create IP Address
            self.log_info("Creating IP address...")
            ip_address = IPAddress(
                address=data["ip_address"],
                status=Status.objects.get(name="Active"),
                assigned_object=interface,
            )
            ip_address.validated_save()
            self.log_success(f"Created IP address: {ip_address.address}")

            return f"Successfully created all records for {data['device_name']}"

        except ValidationError as e:
            self.log_failure(f"Validation error: {str(e)}")
            return f"Failed to create records: {str(e)}"
        except Exception as e:
            self.log_failure(f"Error: {str(e)}")
            return f"Failed to create records: {str(e)}"
