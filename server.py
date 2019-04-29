from flask import Flask,request
import pymongo
import time

MaxUser=10 #最大用户数
MaxTime=30 #房间超时回收时间


app = Flask(__name__)

...
#可以分析两者那些不同 然后更新不同即可
def stateUpdate(id,oldstate,newstate):
    newstate['lastupdatetime']=int(time.time())
    dbcol.update_one({"id":id},{"$set":newstate})


# ... #重置代码
# @app.route('/ResetPort/<id>',methods=['post'])
# def resetting(id):
#     global STATE

#     # 检测id的合法性
#     try:
#         id=int(id)
#         if not 1<=id<=MaxUser:
#             return 'Wrong'
#     except:
#         return 'Wrong'
#     ...#数据库
#     return 'ResetDone'

# 本地主机post文件名
@app.route('/UsefulPort',methods=['post'])
def getUsefulPort():
    filename=request.form['FileName']
    temp=list(dbcol.find({'movie':filename,'person':1}))
    if temp!=[]:
        id=temp[0]['id']
        dbcol.update_one({'id':id},{"$set":{'movie':filename,'person':2,'lastupdatetime':int(time.time())}})
        dbcountcol.insert_one({'id':time.time(),'status':'Match'})
        return '%d:%d'%(id,2)
    temp=list(dbcol.find({'person':0}))
    if temp!=[]:
        id=temp[0]['id']
        print(id)
        dbcol.update_one({'id':id},{"$set":{'movie':filename,'person':1,'lastupdatetime':int(time.time())}})
        return '%d:%d'%(id,1)
    temp=list(dbcol.find({'lastupdatetime':{"$lt": int(time.time())-MaxTime}}))
    if temp!=[]:
        id=temp[0]['id']
        newstate=state.copy()
        for x,y in zip(['id','movie','person','lastupdatetime'],[id,filename,1,int(time.time())]):
            newstate[x]=y
        dbcol.update_one({'id':id},{"$set":newstate})
        return '%d:%d'%(id,1)
    dbcountcol.insert_one({'id':time.time(),'status':'NoUsefulPort'})
    return 'NoUsefulPort'

@app.route('/Port/<id>',methods=['post'])
def running(id):

    # 检测id的合法性
    try:
        id=int(id)
        if not 1<=id<=MaxUser:
            return 'Wrong'
    except:
        return 'Wrong'

    oldstate=dbcol.find_one({'id':id})
    dbcol.update_one({"id":id},{"$set":{'lastupdatetime':int(time.time())}})
    state=oldstate.copy()

    data={
        'from':request.form['from'],
        'type':request.form['type'],
        'text':request.form['text']
        }

    #如果没有两者都ready
    if state['ready']!={'client1':True,'client2':True}:

        if data['type']=='cli-start':
            #设置该client为ready
            state['ready'][data['from']]=True

        #如果两client此时都ready
        if state['ready']=={'client1':True,'client2':True}:
            #服务器同意开始
            state['starttime']=time.time()
        responce='None'
        stateUpdate(id,oldstate,state)
        return responce    #所有return为flask服务器返回post的数据.

    else:
    #如果服务器准备好了

        #如果客户端还在等着开始
        if data['type']=='cli-start':
            responce="%s:%s"%('ser-start',str(state['starttime']))
            return responce

        if 'pause' in data['type']:
            #主动客户端已经暂停，服务器未暂停情况，更改服务器为暂停
            if not state['pauselock'][data['from']]:
                if data['type']=='pauseOn':
                    state['pauselock'][anotherClient[data['from']]]=True
                    state['pause']=True
                    state['pausestarttime']=float(data['text'])+state['starttime']
                    stateUpdate(id,oldstate,state)
                    return 'None'

                #client发送暂停off
                if data['type']=='pauseOff':
                    state['pause']=False
                    clienttime,playtime=map(lambda x:float(x),data['text'].split(':'))
                    # print(clienttime,playtime)
                    state['pausetime']=clienttime-state['starttime']-playtime
                    stateUpdate(id,oldstate,state)
                    return 'None'
                #主动客户端发送pausestatus查询时，不响应
                return 'None'

            #被动客户端监控服务器暂停状态，(此时客户端已经暂停)
            if state['pauselock'][data['from']]:
                #服务器取消暂停，被动客户端接受指令
                if data['type']=='pauseStatus' and not state['pause']:
                    state['pauselock']={'client1':False,'client2':False}
                    nowtime,playtime=time.time(),time.time()-state['starttime']-state['seektime']-state['pausetime']
                    responce='pause:Off:%s:%s'%(str(nowtime),str(playtime) )# 服务器暂停时刻已经播放时间
                    stateUpdate(id,oldstate,state)
                    return responce
                # 被动客户端尝试取消暂停，让被动客户端暂停,并定到服务器暂停位置
                if data['type']=='pauseOff':
                    responce='pauseAndSeek:%s'%(state['pausestarttime']-state['starttime']-state['seektime'] )# 服务器暂停时刻已经播放时间
                    return responce

            return "None"

        #处理一般情况,此时客户端为正常运行状态
        if data['type']=='normal':

            #此时为被动客户端进入暂停处
            if state['pauselock'][data['from']]:
                responce= '%s:%s:%s:%s'%('pause','On',str(time.time()),str(state['pausestarttime']-state['starttime']-state['seektime']))
                return responce
            #正常情况下需要保持服务器和本地时间同步
            else:

                nowtime,playtime=map(float,data['text'].split(':'))
                # 计算客户端和服务器播放时间差距
                delta=nowtime-state['starttime']-state['seektime'] - state['pausetime'] - playtime

                #如果两者都同步播放 释放快进锁,暂停锁
                if abs(delta)<=0.5:
                    state['seeklock']={'client1':False,'client2':False}
                    state['pauselock']={'client1':False,'client2':False}
                    stateUpdate(id,oldstate,state)
                    return 'None'

                #如果客户端和服务器时间差距较大，进入seek模式
                elif abs(delta)>2:

                    #判断为主动客户端
                    if not state['seeklock'][data['from']]:
                        #锁死另一客户端
                        state['seeklock'][anotherClient[data['from']]]=True
                        state['seektime']=nowtime - state['starttime']  - state['pausetime']-  playtime
                        responce ='None'
                        stateUpdate(id,oldstate,state)
                        return responce

                    # 判断为被动客户端
                    # state['seeklock'][data['from']]==True
                    else:
                        responce='%s:%s'%('seek',str(delta))
                        return responce

                #纠正正常卡顿或者其他误差，此时锁死快进锁,暂停锁
                else: 
                    state['seeklock']={'client1':True,'client2':True}
                    state['pauselock']={'client1':True,'client2':True}
                    responce='%s:%s'%('seek',str(delta))
                    stateUpdate(id,oldstate,state)
                    return responce
            return 'None'

if __name__ == '__main__':


    anotherClient={'client1':'client2','client2':'client1'}
    state={'id':0,
        'ready':{'client1':False,'client2':False},
        'pause':False,   #服务器暂停状态
        'starttime':0, #服务器电影开始绝对时间
        'seektime':0,  #主动快进时间
        'pausetime':0,  #所有之前已经暂停时间，是一个不包含此次暂停的所有之前暂停时间总和
        'pausestarttime':0,  # 处理每次暂停时，暂停开始绝对时间
        'seeklock':{'client1':False,'client2':False}, #都为单工，当某client暂停后，另一client只同步服务器暂停状态，本身不能更改服务器状态
        'pauselock':{'client1':False,'client2':False}, #同上
        'person':0, #该房间人数
        'movie':'',   #该房间播放电影名
        'lastupdatetime':0  #该房间数据最近更新时间
        }
    STATE=dict(zip(range(1,MaxUser+1),[state.copy() for _ in range(10)]))

    # mongodb初始化
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["watchwithyou"]

    dbcountcol=mydb['count']
    dbcountcol.delete_many({})
    dbcountcol.insert_one({'id':time.time(),'status':'init'})

    dbcol = mydb["states"]
    dbcol.delete_many({})
    for i in range(1,MaxUser+1):
        state['id']=i
        dbcol.insert_one(state.copy())

    app.run(host='0.0.0.0')

