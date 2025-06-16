import logging

# Changed import path for Job, StringVar, IntegerVar, BooleanVar
from nautobot.apps.jobs import Job, StringVar, IntegerVar, BooleanVar
from nautobot.dcim.models import Device, DeviceType, Manufacturer, Interface, Platform, Location
from nautobot.ipam.models import IPAddress
from nautobot.extras.models import Status
from nautobot.dns.models import Zone, ARecord
from nautobot.apps.jobs import register_jobs # This is crucial for job discovery

# Get an instance of a logger
logger = logging.getLogger(__name__)

class GenerateDevicesAndRecords(Job):
    """
    Nautobot Job to create a specified number of devices with associated
    interfaces, IP addresses, and DNS A records.
    """
    class Meta:
        name = "Generate Devices with IPs and DNS"
        description = "Create a specified number of devices with interfaces, IPs, and A records for testing."
        # Set to True if any input variables contain sensitive data (e.g., API keys, passwords)
        has_sensitive_variables = False
        # Define the category for the job in the Nautobot UI
        task_queue = "default" # Or a specific queue if configured, e.g., "celery_high_priority"

    location_name = StringVar(
        description="Name of the Location to place all devices under. Will be created if it doesn't exist.",
        default="AutoLab",
        required=True
    )

    base_device_name = StringVar(
        description="Base prefix for device names (e.g., 'autodev'). Devices will be named 'autodev-0', 'autodev-1', etc.",
        default="autodev",
        required=True
    )

    total_devices = IntegerVar(
        description="Number of devices to create. Be mindful of resource usage for large numbers.",
        default=100, # Reduced default for safer initial runs
        min_value=1,
        max_value=5000, # Added a max value for safety
        required=True
    )

    zone_name = StringVar(
        description="DNS Zone (e.g., example.com). Will be created if it doesn't exist.",
        default="example.com",
        required=True
    )

    dry_run = BooleanVar(
        description="If true, no changes will be made to the database. Only simulates the actions.",
        default=True
    )

    def run(self, data, commit):
        """
        Main execution method for the job.
        Args:
            data (dict): Dictionary of input variables as defined in the Job class.
            commit (bool): Indicates if changes should be committed to the database.
                           This is effectively `not self.dry_run`.
        """
        self.log_info(f"Starting device generation job. Dry run: {data['dry_run']}")

        if data["total_devices"] <= 0:
            self.log_failure("Total devices must be a positive integer.")
            return

        # Use commit to respect the dry_run flag
        if not commit:
            self.log_warning("Dry run mode: No changes will be committed to the database.")

        try:
            # 1. Prepare common objects using get_or_create for idempotency
            # Ensure statuses exist
            status_active, _ = Status.objects.get_or_create(
                name="Active", defaults={"description": "Active status"}
            )
            # Ensure manufacturer exists
            manufacturer, created = Manufacturer.objects.get_or_create(name="AutoGen Inc.")
            if created:
                self.log_info(f"Created new Manufacturer: {manufacturer.name}")

            # Ensure device type exists
            device_type, created = DeviceType.objects.get_or_create(
                model="AGen-Switch", manufacturer=manufacturer,
                defaults={"slug": "agen-switch"} # Slug is required for DeviceType
            )
            if created:
                self.log_info(f"Created new DeviceType: {device_type.model}")

            # Ensure platform exists
            platform, created = Platform.objects.get_or_create(name="AutoOS")
            if created:
                self.log_info(f"Created new Platform: {platform.name}")

            # Ensure location exists
            location, created = Location.objects.get_or_create(name=data["location_name"])
            if created:
                self.log_info(f"Created new Location: {location.name}")

            # Ensure DNS zone exists
            zone, created = Zone.objects.get_or_create(name=data["zone_name"])
            if created:
                self.log_info(f"Created new DNS Zone: {zone.name}")

            created_count = 0
            for i in range(data["total_devices"]):
                device_name = f"{data['base_device_name']}-{i}"
                # Simple IP address generation for demonstration
                # Consider more robust IP management for real-world use cases
                ip_str = f"10.0.{(i // 256) % 256}.{i % 256}/24" # Added modulo 256 for the third octet

                self.log_info(f"Processing device: {device_name} with IP: {ip_str}")

                # 2. Create or get Device
                # Using update_or_create to make the job idempotent if run multiple times
                device, created = Device.objects.update_or_create(
                    name=device_name,
                    defaults={
                        "device_type": device_type,
                        "platform": platform,
                        "location": location,
                        "status": status_active,
                    }
                )
                if created:
                    self.log_success(f"Device '{device_name}' created.")
                    created_count += 1
                else:
                    self.log_info(f"Device '{device_name}' already exists. Updating...")

                # 3. Add or get interface
                interface, created = Interface.objects.update_or_create(
                    device=device,
                    name="eth0",
                    defaults={
                        "type": "1000base-t",
                        "status": status_active,
                    }
                )
                if created:
                    self.log_success(f"Interface 'eth0' for '{device_name}' created.")
                else:
                    self.log_info(f"Interface 'eth0' for '{device_name}' already exists. Updating...")

                # 4. Add or get IP Address and bind it to interface
                ip_address_obj, created = IPAddress.objects.update_or_create(
                    address=ip_str,
                    defaults={
                        "assigned_object": interface,
                        "status": status_active,
                    }
                )
                if created:
                    self.log_success(f"IP Address '{ip_str}' for '{device_name}' created and assigned to interface.")
                else:
                    self.log_info(f"IP Address '{ip_str}' for '{device_name}' already exists. Updating...")


                # 5. Add or get A Record
                # Note: ARecord 'address' field expects an IPAddress object.
                arecord, created = ARecord.objects.update_or_create(
                    name=device_name,
                    zone=zone,
                    defaults={
                        "address": ip_address_obj # Pass the IPAddress object
                    }
                )
                if created:
                    self.log_success(f"A Record for '{device_name}.{zone.name}' pointing to '{ip_address_obj.address}' created.")
                else:
                    self.log_info(f"A Record for '{device_name}.{zone.name}' already exists. Updating...")

                self.log_info(f"Processed {device_name} | IP: {ip_str}")

            if commit:
                self.log_success(f"✅ Done! Created/Updated {created_count} new devices and processed a total of {data['total_devices']} devices in zone '{zone.name}'.")
            else:
                self.log_success(f"✅ Dry run complete! Would have created/updated {created_count} new devices and processed a total of {data['total_devices']} devices in zone '{zone.name}'. No changes were made.")

        except Exception as e:
            self.log_failure(f"An unexpected error occurred: {e}")
            logger.exception("Error during job execution")

# The register_jobs call is essential. It tells Nautobot to find this job.
register_jobs(GenerateDevicesAndRecords)
