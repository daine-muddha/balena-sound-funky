from flask import Flask
from flask import render_template, redirect, request, url_for, render_template_string
from config import Config
from data import Data
from forms import SocketAssignmentForm, AudioOutputForm, RadioSettingsForm, RadioSelectionForm
from helpers import get_pcm_and_ctl
from py_crontab import update_timer_switches
from time import sleep
from werkzeug.datastructures import MultiDict

import json
import os
import re
import subprocess
import time
import urllib.parse

app = Flask(__name__)
app.config.from_object(Config)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/funky', methods=['GET', 'POST'])
def funky():
    if request.method == 'GET':
        with open(Data.url) as file:
            data = json.load(file)
            categories = dict()
            #create dictionary where the keys are the different categories and the value is a list of the dicts containing a socket of this category
            for funk in data["funksteckdosen"]:
                if funk["category"]=='Unbelegt':
                    continue
                else: 
                    category = categories.get(funk["category"], None)
                    if category is None:
                        categories[funk["category"]] = [funk]
                    else:
                        category.append(funk)
                        categories[funk["category"]] = category
            #convert dictionary to a list where each entry is a dictionary with one key/val pair being the name of this category 
            #and the other key/val pair being the list of dictionaries for this category (for template)
            cat_list = list()
            for key, val in categories.items():
                temp_dict = dict()
                temp_dict["name"] = key
                temp_dict["sockets"] = val
                cat_list.append(temp_dict)

        return render_template('funky.html', categories=cat_list)

    elif request.method == 'POST':
        btn_id = request.form['btn_id']
        btn_id = btn_id.split('+')
        try:
            os.system('rfsniffer -b "/data/buttons.db" play {}.{}{}'.format(btn_id[0].lower(), btn_id[1], btn_id[2]))
            return 'OK'
        except:
            return redirect(url_for('ooops'))
        

@app.route('/settings/sockets', methods=['GET', 'POST'])
def socket_settings():
    if request.method == 'GET':
        with open(Data.url) as file:
            data = json.load(file)
            forms = list()
            for funk in data["funksteckdosen"]:
                form = SocketAssignmentForm(MultiDict(funk))
                forms.append(form)
        return render_template('socket_settings.html', forms=forms)
    elif request.method == 'POST':
        form_data = request.form['form_data']
        form_data = form_data.replace('=y&', '=true&')
        form_data = form_data.split('&formbreak&')
        form_data = form_data[:-1]
        json_list = list()
        for form in form_data:
            form_dict = urllib.parse.parse_qs(form)
            form_dict = {key:val[0] for key,val in form_dict.items()}
            form_obj = SocketAssignmentForm(MultiDict(form_dict))
            form_obj_data = form_obj.data
            form_obj_data.pop('csrf_token', None)
            json_list.append(form_obj_data)
        with open(Data.url, 'r') as file:
            data = json.load(file)
        data["funksteckdosen"] = json_list
        with open(Data.url, 'w') as file:
            json.dump(data, file, indent=4)
        update_timer_switches()
        return redirect(url_for('index'))


@app.route('/settings/radio', methods=['GET', 'POST'])
def radio_settings():
    if request.method == 'GET':
        with open(Data.url) as file:
            data = json.load(file)
        radios = data.get('radios', None)
        forms = list()
        if radios is not None:
            for radio in radios:
                form = RadioSettingsForm(MultiDict(radio))
                forms.append(form)
        return render_template('radio_settings.html', forms=forms)

    elif request.method == 'POST':
        form_data = request.form.get('form_data', None)
        if form_data is not None:
            form_data = form_data.split('&formbreak&')
            form_data = form_data[:-1]
            json_list = list()
            for form in form_data:
                form_dict = urllib.parse.parse_qs(form)
                form_dict = {key:val[0] for key,val in form_dict.items()}
                form_obj = RadioSettingsForm(MultiDict(form_dict))
                form_obj_data = form_obj.data
                form_obj_data.pop('csrf_token', None)
                json_list.append(form_obj_data)
            with open(Data.url, 'r') as file:
                data = json.load(file)
            data["radios"] = json_list
            with open(Data.url, 'w') as file:
                json.dump(data, file, indent=4)
            return redirect(url_for('index'))
        add_form = request.form.get('add_form', None)
        if add_form is not None:
            form = RadioSettingsForm()
            data = render_template('radio_settings_form.html', form=form)
            return data

"""
@app.route('/music', methods=['GET', 'POST'])
def music():
    min_volume=0
    max_volume=10639
    pcm_output_bt = 'pcm.output {\n\ttype bluealsa\n\tdevice "[MAC]"\n\tprofile "a2dp"\n}'
    ctl_default_bt = 'ctl.!default {\n\ttype bluealsa\n}'
    pcm_output_card = 'pcm.output {\n\ttype hw\n\tcard 0\n}'
    ctl_default_card = 'ctl.!default {\n\ttype hw\n\tcard 0\n}'
    if request.method == 'GET':
        #get audio output
        process = subprocess.Popen(['amixer', 'cget', 'numid=3'], stdout=subprocess.PIPE)
        stdout = process.communicate()[0].decode('utf-8')
        audio_out_val_str = stdout.split(':')[-1]
        search_str = 'values='
        audio_out_val_ind=audio_out_val_str.find(search_str)+len(search_str)
        bt_cons = list()
        for bt_mac in ['00:E0:4C:7E:46:38', '2C:41:A1:2D:C7:51']:
            bt_input = f'info {bt_mac}'.encode('utf-8')
            bt_process = subprocess.run(['sudo', 'bluetoothctl'], stdout=subprocess.PIPE, input=bt_input)
            bt_stdout = bt_process.stdout.decode('utf-8')
            if 'Connected: no' in bt_stdout:
                bt_con = False
            elif 'Connected: yes' in bt_stdout:
                bt_con = True
            bt_cons.append(bt_con)
        print(bt_cons)
        try:
            audio_out_val = audio_out_val_str[audio_out_val_ind]
        except:
            asound_content, pcm_output, ctl_default = get_pcm_and_ctl()
            asound_content = asound_content.replace(pcm_output, pcm_output_card)
            asound_content = asound_content.replace(ctl_default, ctl_default_card)
            with open('/home/pi/.asoundrc', 'w') as file:
                file.write(asound_content)
            audio_out_val = '1'
        audio_output=''
        alsa_scontrol = 'PCM'
        if audio_out_val=='0':
            audio_output='auto'
        elif audio_out_val=='1':
            audio_output='box'
        elif audio_out_val=='2':
            audio_output='hdmi'
        else:
            output_info = stdout.split(':')[0]
            if 'SoundCore mini' in output_info:
                audio_output =  'bt_anker'
                alsa_scontrol = '"SoundCore mini - A2DP"'
            elif 'LE-Bose Micro SoundLin' in output_info:
                audio_output = 'bt_bose'
                alsa_scontrol =  '"LE-Bose Micro SoundLi - A2DP"'
        audio_output_form = AudioOutputForm(audio_output=audio_output)
        #get volume
        process = subprocess.Popen(['amixer', '-M', 'sget', alsa_scontrol], stdout=subprocess.PIPE)
        stdout = process.communicate()[0].decode('utf-8')
        output_split = stdout.split(':')
        volume_str = output_split[-1]
        search_str = '['
        volume_start_ind=volume_str.find(search_str)+len(search_str)
        volume_end_ind = volume_str.find('%')
        try:
            volume = int(volume_str[volume_start_ind:volume_end_ind])
        except:
            volume = 'Error'
        #get radio stations
        with open(Data.url) as file:
            data = json.load(file)
        radios = data.get('radios', None)

        if radios is not None:
            name_list = list()
            url_list = list()
            for radio in radios:
                name_list.append(radio["name"])
                url_list.append(radio["url"])
            radio_station_form = RadioSelectionForm()
            radio_station_form.radio.choices = [(x.lower(), x) for x in name_list]


        return render_template('music.html', volume=volume, audio_output_form=audio_output_form, radio_station_form=radio_station_form, url_list=url_list, bt_cons=bt_cons)
    elif request.method == 'POST':
        volume = request.form.get('volume', None)
        audio_output = request.form.get('audio_output', None)
        if volume is not None:
            if audio_output in ['auto', 'box', 'hdmi']:
                alsa_scontrol='PCM'
            elif audio_output == 'bt_anker':
                alsa_scontrol = '"SoundCore mini(ATT) - A2DP"'
            elif audio_output == 'bt_bose':
                alsa_scontrol =  '"LE-Bose Micro SoundLi - A2DP"'
            try:
                volume= int(volume)
                os.system('amixer -q -M sset {} {}%'.format(alsa_scontrol, volume))
                return 'OK'
            except:
                return 'Not OK'

        
        if audio_output is not None:
            asound_content, pcm_output, ctl_default = get_pcm_and_ctl()
            if audio_output in ['auto', 'box', 'hdmi']:
                if audio_output=='auto':
                    audio_out_val=0
                elif audio_output=='box':
                    audio_out_val=1
                elif audio_output=='hdmi':
                    audio_out_val=2
                if pcm_output != pcm_output_card:
                    asound_content = asound_content.replace(pcm_output, pcm_output_card)
                    asound_content = asound_content.replace(ctl_default, ctl_default_card)
                    with open('/home/pi/.asoundrc', 'w') as file:
                        file.write(asound_content)
                    try:
                        os.system('sudo service raspotify restart')
                        os.system('killall vlc')
                    except:
                        pass
                try:
                    os.system('amixer cset numid=3 {}'.format(audio_out_val))
                    return 'OK'
                except:
                    return 'Not OK'
            else:
                if audio_output=='bt_anker':
                    bt_mac = '00:E0:4C:7E:46:38'
                elif audio_output=='bt_bose':
                    bt_mac = '2C:41:A1:2D:C7:51'
                pcm_new_output = pcm_output_bt.replace('[MAC]', bt_mac)
                try:
                    os.system('echo "connect {}" | sudo bluetoothctl'.format(bt_mac))
                    asound_content, pcm_output, ctl_default = get_pcm_and_ctl()
                    asound_content = asound_content.replace(pcm_output, pcm_new_output)
                    if ctl_default!=ctl_default_bt:
                        asound_content = asound_content.replace(ctl_default, ctl_default_bt)
                    with open('/home/pi/.asoundrc', 'w') as file:
                        file.write(asound_content)
                    try:
                        os.system('sudo service raspotify restart')
                        os.system('killall vlc')
                    except:
                        pass
                    return 'OK'
                except:
                    return 'Not OK'

        radio_play = request.form.get('radio_play', None)
        if radio_play is not None:
            try:
                os.system('killall vlc')
                cmd = ['cvlc', '--aout', 'alsa', '{}'.format(radio_play)]
                radio_process = subprocess.Popen(cmd)
                return 'OK'
            except:
                return 'Not OK'
        radio_stop = request.form.get('radio_stop', None)
        if radio_stop is not None:
            try:
                os.system('killall vlc')
                return 'OK'
            except:
                return 'Not OK'
"""
@app.route('/settings/power', methods=['GET', 'POST'])
def raspbi_power():
    if request.method == 'GET':
        return render_template('ooops.html')
    elif request.method == 'POST':
        btn_id = request.form.get('btn_id', None)
        if btn_id == 'powerBtn':
            try:
                os.system('sudo poweroff')
                return 'OK'
            except:
                return 'Not OK'
        elif btn_id == 'rebootBtn':
            try:
                os.system('sudo reboot')
                return 'OK'
            except:
                return 'Not OK'
        else:
            return 'Not OK'

@app.route('/ooops')
def ooops():
    return render_template('ooops.html')


if __name__=='__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
