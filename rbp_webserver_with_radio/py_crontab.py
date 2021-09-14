from crontab import CronTab
import json

from data import Data

def update_or_create_job(cron, funk, job_id, time_key):
    job_list = list(cron.find_comment(job_id))
    job_list_len = len(job_list)
    if job_list_len==1:
        job = job_list[0]
    elif (job_list_len>1)|(job_list_len==0):
        for job in job_list:
            cron.remove(job)
        turn = ''
        if time_key=='start':
            turn='on'
        elif (time_key=='end') | (time_key=='auto_off_at'):
            turn='off'
        command_str = 'sh /home/pi/activate_timer_switch.sh {}.{}{}'.format(funk["remote"].lower(), funk["socket"], turn)
        job = cron.new(command=command_str, comment=job_id)
    times = funk[time_key].split(':')
    hour = int(times[0])
    minute = int(times[1])
    weekdays_str = ''
    if time_key in ['start', 'end']:
        weekdays = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        weekdays_str = ''
        for i in range(len(weekdays)):
            if funk[weekdays[i]]==True:
                weekdays_str+='{},'.format(i)
    elif time_key == 'auto_off_at':
        weekdays_str='*'
    if len(weekdays_str)==0:
        cron.remove(job)
    else:
        if time_key != 'auto_off_at':
            weekdays_str = weekdays_str[:-1]
        set_all_str = '{} {} * * {}'.format(minute, hour, weekdays_str)
        job.setall(set_all_str)

    return cron

def update_timer_switches():
    cron = CronTab(user='pi')
    with open(Data.url) as file:
        data = json.load(file)

    socket_timer_disabled_list = list()

    for funk in data["funksteckdosen"]:
        if funk["timer_switch"]==False:
            socket_timer_disabled_list.append('socket_{}{}_on'.format(funk["remote"], funk["socket"]))
            socket_timer_disabled_list.append('socket_{}{}_off'.format(funk["remote"], funk["socket"]))

    current_jobs = [job.comment for job in cron]

    for socket_timer_disabled in socket_timer_disabled_list:
        job_list = list(cron.find_comment(socket_timer_disabled))
        for job in job_list:
            cron.remove(job)

    for funk in data["funksteckdosen"]:
        if funk["timer_switch"]==True:
            socket_timer_on = 'socket_{}{}_on'.format(funk["remote"], funk["socket"])
            socket_timer_off = 'socket_{}{}_off'.format(funk["remote"], funk["socket"])
            cron = update_or_create_job(cron, funk, socket_timer_on, 'start')
            cron = update_or_create_job(cron, funk, socket_timer_off, 'end')
        elif funk["auto_off"]==True:
            socket_timer_auto_off = 'socket_{}{}_auto_off'.format(funk["remote"], funk["socket"])
            cron = update_or_create_job(cron, funk, socket_timer_auto_off, 'auto_off_at')

    cron.write()



