import string

template = string.Template("""
# Show what aspects might need attention
cobbler check

# Act on the 'check' above, then re-check until satisfactory.
# (Details beyond the scope of this particular example.)

# Import a client OS from a DVD.  This automatically sets up a "distro" and names it.
# (See below ISO file variant.)
cobbler import --path=$__contrail_distro_path__ --name=$__contrail_distro_prefix__ --arch=x86_64

# Create a profile (e.g. "rhel5_workstation") and associate it with that distro
cobbler profile add --name=$__contrail_profile_name__ --distro=${__contrail_distro_prefix__}-x86_64

# Set up a kickstart file.
# (Details beyond the scope of this particular example.)

# Associate a kickstart file with this profile
cobbler profile edit --name=$__contrail_profile_name__ --kickstart=$__contrail_kickstart_config__

# Register a client machine (e.g. "workstation1") and its network details
# and associate it with a profile
$__contrail_cobbler_system_add_commands__

# Get a detailed report of everything in cobbler
cobbler report

# Get cobbler to act on all the above (set up DHCP, etc.)
cobbler sync
""")
