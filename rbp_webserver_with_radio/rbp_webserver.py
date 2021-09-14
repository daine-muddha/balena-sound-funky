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


@app.route('/', methods=['GET', 'POST'])
def index():
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
            
            #get volume
            process = subprocess.Popen(['amixer', '-M', 'sget', 'Master'], stdout=subprocess.PIPE)
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
            radios = data.get('radios', None)
            if radios is not None:
                name_list = list()
                url_list = list()
                for radio in radios:
                    name_list.append(radio["name"])
                    url_list.append(radio["url"])
                radio_station_form = RadioSelectionForm()
                radio_station_form.radio.choices = [(x.lower(), x) for x in name_list]

        return render_template('index.html', categories=cat_list, radio_station_form=radio_station_form, url_list=url_list, volume=volume)

    elif request.method == 'POST':
        btn_id = request.form.get('btn_id', None)
        if btn_id is not None:
            btn_id = btn_id.split('+')
            try:
                os.system('rfsniffer -b "/data/buttons.db" play {}.{}{}'.format(btn_id[0].lower(), btn_id[1], btn_id[2]))
                return 'OK'
            except:
                return redirect(url_for('ooops'))
        volume = request.form.get('volume', None)
        if volume is not None:
            try:
                volume= int(volume)
                os.system('amixer -q -M sset Master {}%'.format(volume))
                return 'OK'
            except:
                return 'Not OK'
        radio_play = request.form.get('radio_play', None)
        if radio_play is not None:
            try:
                os.system('pkill vlc')
                os.system("sed -i s/geteuid/getppid/ /usr/bin/vlc")
                cmd = ['cvlc', '--aout', 'alsa', '{}'.format(radio_play)]
                radio_process = subprocess.Popen(cmd)
                return 'OK'
            except:
                return 'Not OK'
        radio_stop = request.form.get('radio_stop', None)
        if radio_stop is not None:
            try:
                os.system('pkill vlc')
                return 'OK'
            except:
                return 'Not OK'

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


@app.route('/settings/power', methods=['GET', 'POST'])
def raspbi_power():
    if request.method == 'GET':
        return render_template('ooops.html')
    elif request.method == 'POST':
        btn_id = request.form.get('btn_id', None)
        if btn_id == 'powerBtn':
            try:
                #os.system('sudo poweroff')
                return 'OK'
            except:
                return 'Not OK'
        elif btn_id == 'rebootBtn':
            try:
                #os.system('sudo reboot')
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
