# tag2targetgroup
Takes all the assets with certain tags in Tenable.io and creates a target group based on those assets.  This allows scanning, reporting, and RBAC rules by tags.

# Getting Help
`./tag2targetgroup.py -h`

# Connecting to Tenable.io
To use this script, you will need an Tenable.io API access key and secret key.  Tenable.io API keys can be retrieved by going into your Tenable.io instance, clicking on Settings, clicking on My Account, and then clicking API Keys.  Once you have the API keys, you need to provide them to the script.  That can be done by setting the environment variables TIOACCESSKEY and TIOSECRETKEY, or by providing on the command line (which is less secure).

# Providing Tenable.io access key and secret key by environment variable

Below is an example of using the script and providing the API keys via environment variables.

```bash$ export TIOACCESSKEY==********************************************

bash$ export TIOSECRETKEY=********************************************

bash$ ./tag2targetgroup.py --tagname criticality --tagvalue high --targetgroup "Critical assets" ```

# Providing Tenable.io access key and secret key by CLI
Providing the API keys on the command line is not recommended because the CLI history is stored, which could allow someone to retrieve your API keys.  Sometimes the need comes up, so this is an example of how to run the script by providing the API keys on the CLI:

`bash$ ./tag2targetgroup.py --accesskey ********* --secretkey ********* --tagname criticality --tagvalue high --targetgroup "Critical assets"`

# Create a target group based on operating system
This example creates a target group called "Windows Systems".  This assumes a Tenable.io tag has been created that has the name "os" and has the value "windows".  Ideally that tag should have an automatical matching rule to add the tag to anything with the "Operating System" containing "Windows"

`./tag2targetgroup.py --tagname os --tagvalue windows --targetgroup "Windows Systems" `


# Create a target group based on multiple tags
This example creates a target group called "Windows Systems".  This assumes there are multiple Tenable.io tags that have been created that tag various windows systems.  Ideally that tag should have an automatical matching rule to add the tag to anything with the "Operating System" containing "Windows"

```./tag2targetgroup.py --tagname os --tagvalue "Windows Desktops" --targetgroup "Windows Systems" 

./tag2targetgroup.py --tagname os --tagvalue "Windows Servers" --targetgroup "Windows Systems" --append```



