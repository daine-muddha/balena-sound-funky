import re

def get_pcm_and_ctl():
    with open('/home/pi/.asoundrc', 'r') as file:
        asound_content = file.read()
    pcm_output = re.search('(?s)(pcm.output )(.*?)(\})', asound_content).group()
    ctl_default = re.search('(?s)(ctl.!default )(.*?)(\})', asound_content).group()

    return asound_content, pcm_output, ctl_default