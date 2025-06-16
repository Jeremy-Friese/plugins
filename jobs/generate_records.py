from nautobot.core.jobs import Job, StringVar, IntegerVar
from nautobot.dcim.models import Device, DeviceType, Manufacturer, Interface, Platform, Location
from nautobot.ipam.models import IPAddress
from nautobot.extras.models import Status
from nautobot.dns.models import Zone, ARecord

from django.utils.text import slugify


class GenerateDevicesAndRecords(Job):
    class Meta:
        name = "Generate Devices with IPs and DNS"
        description = "Create 1000 devices with interfaces, IPs, and A records"
        has_sensitive_variables = False

    location_name = StringVar(
        description="Name of the Location to place all devices under", default="AutoLab"
    )

    base_device_name = StringVar(
        description="Base prefix for device names (e.g., 'autodev')", default="autodev"
    )

    total_devices = IntegerVar(
        description="Number of devices to create", default=1000
    )

    zone_name = StringVar(
        description="DNS Zone (e.g., example.com)", default="example.com"
    )

    def run(self, data, commit):
        # 1. Prepare common objects
        status_active = Status.objects.get(name="Active")
        manufacturer, _ = Manufacturer.objects.get_or_create(name="AutoGen Inc.")
        device_type, _ = DeviceType.objects.get_or_create(
            model="AGen-Switch", manufacturer=manufacturer
        )
        platform, _ = Platform.objects.get_or_create(name="AutoOS")
        location, _ = Location.objects.get_or_create(name=data["location_name"])
        zone, _ = Zone.objects.get_or_create(name=data["zone_name"])

        for i in range(data["total_devices"]):
            device_name = f"{data['base_device_name']}-{i}"
            ip_str = f"10.0.{i // 256}.{i % 256}/24"

            # 2. Create Device
            device = Device.objects.create(
                name=device_name,
                device_type=device_type,
                platform=platform,
                location=location,
                status=status_active,
            )

            # 3. Add interface
            interface = Interface.objects.create(
                device=device,
                name="eth0",
                type="1000base-t",
                status=status_active,
            )

            # 4. Add IP Address and bind it to interface
            ip = IPAddress.objects.create(
                address=ip_str,
                assigned_object=interface,
                status=status_active,
            )

            # 5. Add A Record
            ARecord.objects.create(
                name=device_name,
                zone=zone,
                address=ip
            )

            self.log_success(f"Created {device_name} | IP: {ip_str}")

        self.log_success(f"✅ Done! {data['total_devices']} devices created in zone '{zone.name}'.")

job = GenerateDevicesAndRecords
