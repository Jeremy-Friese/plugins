from nautobot.extras.plugins import PluginConfig

class JobsPluginConfig(PluginConfig):
    name = "jobs"
    verbose_name = "Jobs Plugin"
    description = "Plugin for custom jobs"
    version = "1.0"
    author = "Your Name"
    author_email = "your.email@example.com"
    required_settings = []
    default_settings = {}

config = JobsPluginConfig
