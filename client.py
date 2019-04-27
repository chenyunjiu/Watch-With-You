from requests import post
import os 
import sys
from time import time as timetime
from time import sleep as timesleep
from  base64 import b64encode
from mpv_python_ipc import MpvProcess
import tkinter as tk
from tkinter import filedialog,messagebox

# 弹出窗口并退出程序
def messageandquit(text,text2):
    messagebox.showinfo(text,text2)
    # mp.process.kill()
    os.system("taskkill /t /f /pid %s" % mp.process.pid)
    sys.exit()

# 获取文件名称
def chooseFile():
    # 获取播放文件路径
    
    root = tk.Tk()
    root.withdraw()
    ... #限制文件类型
    if debug:
        filepath="C:/Users/lieber/Desktop/Apple won't like this... - Run MacOS on ANY PC.mp4"
    else:
        filepath = filedialog.askopenfilename(initialdir = "\\",title = "选择电影文件")
    del root
    return filepath

# 获取可用房间Id和mateId
def getusefulId(filepath):
    # 获取文件名 转为hash或者怎样
    ...
    Filename=str(b64encode(filepath.split('/')[-1].encode('utf-8')),'utf-8')[:20]
    postdata = {'FileName':Filename}
    # 检测服务器是否开启
    try:
        rtext=post(server+'/UsefulPort',data=postdata).text.strip()
    except:
    # 服务器未开启，弹出窗口 关闭程序
        messageandquit('错误','服务器未打开！')
    if rtext=='NoUsefulPort':
        messageandquit('错误','服务器现在用户已满！')
    else:
        ... #弹出窗口
        # messagebox.showinfo('提示(需要主动关闭该窗口)','已连接服务器等待配对，请勿关闭程序')
        Id,Mateid=map(lambda x:int(x),rtext.split(':'))
    return Id,Mateid


def keepMPVSynchronize(server,Id,Mateid,filepath,HEARTTIME,debug=False):

    server=server+'/Port/%d'%Id
    clientname= 'client1' if Mateid== 1 else 'client2'
    postdata = {'from':clientname,'type':'cli-start','text':''}

    print('loadfile %s '%('"'+filepath+'"'))

    # 打开mpv进程
   
    mp.slave_command('loadfile %s '%('"'+filepath+'"'))
    if debug:
        mp.slave_command('set window-scale 0.5')
    mp.slave_command('set pause yes')
    mp.slave_command('seek 0 absolute')


    try:
        while True:
            timesleep(0.5)
            #告诉服务器 该client ready
            rtext=post(server,data=postdata).text.strip()
            #待服务器ready后，返回
            if rtext!='None':
                if rtext.split(':')[0]=='ser-start':
                    # print(rtext)
                    deleta=timetime()-float(rtext.split(':')[1])

                    mp.slave_command('seek %s absolute'%deleta)
                    mp.slave_command('set pause no')
                    break

        pauseFlag=False
        while True:
            #一直控制，保持和服务器同步
            timesleep(HEARTTIME)
            nowtime=timetime()   #本地绝对时间 
            playtime=float(mp.get_property('playback-time')) if mp.get_property('playback-time') else 0#电影播放时间

            #该client为正常播放状态
            if not pauseFlag:
                #播放器暂停时,向服务器发送暂停指令
                if mp.get_property('pause')=='yes':
                    pauseFlag=True
                    postdata['type']='pauseOn'
                    postdata['text']=str(playtime)
                    post(server,data=postdata).text.strip()
                    continue
                #正常情况下,发送该client播放时间,等待服务器指令
                else:
                    postdata['type']='normal'
                    postdata['text']='%s:%s'%(str(nowtime),str(playtime))
                    rtext=post(server,data=postdata).text.strip()

                    #如果服务器没有指令，继续循环
                    if rtext=='None':
                        continue

                    #被动客户端
                    #pause表示服务器已经暂停，本地需要暂停
                    elif 'pause:On'in rtext: 
                        mp.slave_command('set pause yes')
                        server_time,server_playtime=map(lambda x: float(x),rtext.split(':')[-2:])
                        mp.slave_command('seek %s absolute'%str(nowtime-server_time+server_playtime))
                        pauseFlag=True
                        continue
                    #服务器有指令时
                    #seek为本地播放时间和服务器不同步时，主动同步到服务器播放时间
                    #"seek:2.2" 指令:差距时间
                    elif 'seek' in rtext:
                        delta=float(rtext.split(':')[1])
                        nowplaytime=float(mp.get_property('playback-time'))
                        server_playtime=nowplaytime+delta
                        mp.slave_command('seek %s absolute'%str(server_playtime))
                        continue

            #当该client暂停的时候，现在只需要监测该client和服务器是否结束暂停
            #pauseFlag==True
            else:
                #该client已经不再暂停，让服务器解除暂停
                if mp.get_property('pause')=='no':
                    pauseFlag=False
                    postdata['type']='pauseOff'
                    postdata['text']='%s:%s'%(str(nowtime),str(playtime))
                    rtext=post(server,data=postdata).text.strip()
                    
                    # print(rtext)
                    #防止被动客户端主动取消暂停
                    if 'pauseAndSeek' in rtext:
                        server_playtime=float(rtext.split(':')[1])
                        pauseFlag=True
                        mp.slave_command('set pause yes')
                        mp.slave_command('seek %s absolute'%str(server_playtime))

                #该client仍然处于暂停阶段
                #为被动客户端结束暂停
                # mp.get_property('pause')=='yes'
                else:
                    postdata['type']='pauseStatus'
                    postdata['text']=''
                    ... #待修改
                    rtext=post(server,data=postdata).text.strip()
                    #服务器已经不再暂停，被动客户端也不暂停
                    if 'pause:Off' in rtext:
                        server_time,server_playtime=map(lambda x: float(x),rtext.split(':')[-2:])
                        mp.slave_command('set pause no')
                        mp.slave_command('seek %s absolute'%str(nowtime-server_time+server_playtime))
                        pauseFlag=False
                    continue

    finally:
        mp.process.kill()


if __name__ == '__main__':
	
    with open('config.ini','r',encoding='utf-8') as file:
        server=file.readline().strip()[1:]  #sig问题
        HEARTTIME=eval(file.readline().strip())
        debug=True if file.readline().strip() =='Debug' else False

    mp = MpvProcess()

    filepath=chooseFile()
    print(filepath)
    Id,Mateid=getusefulId(filepath)
    print(Id,Mateid)

    keepMPVSynchronize(server,Id,Mateid,filepath,HEARTTIME,debug)
