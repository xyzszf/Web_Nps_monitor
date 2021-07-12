# -*- coding: UTF-8 -*- 

# 项目名称：WEB Auto Monitor V4，采用aiohttp，真正实现异步并行方法
# 项目描述：对web url进行定期拨测，拨测结果如果有需要可以记录到数据看，并且可以自动发送告警邮件
# 作者：邵壮丰
# 时间：2020年3月15日

# 
import requests,time,re,datetime
import pandas as pd

#如果需要保存到数据库的话，使用下面一行倒入配置
#from sqlalchemy import create_engine
# from config import db_uri 

import asyncio 
from email.message import EmailMessage
import aiosmtplib
import aiohttp

#显示所有列
pd.set_option('display.max_columns', None)
#显示所有行
pd.set_option('display.max_rows', None)
#设置value的显示长度为100，默认为50
pd.set_option('max_colwidth',200)
#True就是可以换行显示。设置成False的时候不允许换行
pd.set_option('expand_frame_repr', False)
# pd.set_option('colheader_justify', 'right')

# 这个特殊函数，用于串行对web url进行拨测，每次只采集一个url 
# @asyncio.coroutine 这是老的写法，参考https://www.liaoxuefeng.com/wiki/1016959663602400/1048430311230688
async def test_url(url):
	test_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
	# 由于为了在打印出来的url中增加url的名称或联系人等信息，因此函数传进来的一个没有预处理的完整文本行，
	# 下面使用正则表达式实现把其中的url“http”开头的子串取出来,记录为val_url(有效的url的意思)，送入到requests.get中
	# 然后在输出或者返回中，仍然把原始的url完整串返回或打印
	# #group()是取正则对象的值,参考https://www.runoob.com/python/python-reg-expressions.html，http 开头字符 \S 任意字符 *多个字符，r'http\S*' 目标patten
	val_url = re.search(r'http\S*',url).group() 

	timeout = aiohttp.ClientTimeout(total=2) #设置超时时间
	try:
		t0 = time.time()
		# res = requests.get(val_url,timeout=5)
		async with aiohttp.request('GET',val_url,timeout=timeout) as res: #由于使用requests是同步的，采用aiohttp是异步
			pass
		t1 = time.time()
		# test_result = [test_time,url,res.status_code,res.ok,str(res.elapsed)]
		test_result = [test_time,url,res.status,t1-t0]
	except Exception as e:
		test_result = [test_time,url,None,None]
	return test_result

# 批量测试函数
async def banch_test_url(loop,urls):
	tasks = [asyncio.ensure_future(test_url(url)) for url in urls]
	responses = await asyncio.gather(*tasks)
	return responses

# 把拨测结果自动发送邮件，mess_cont是外部引入的要发送的内容
async def auto_sent_mail(mess_cont,mail_to):
    message = EmailMessage()
    message["From"] = "xyzszf@163.com"
    message["To"] = mail_to
    message["Subject"] = "广东电信IPTV WEB拨测告警"
    # message.set_content("Sent via aiosmtplib")
    message.set_content(mess_cont)

    #设置smtp参数
    await aiosmtplib.send(message,
        hostname="smtp.163.com",
        port=465, 
        use_tls=True, #不加密，这项去掉
        username= "", #邮箱地址
        password = "" #smtp密码
    )

if __name__ == '__main__':

	#设定要拨测的时间间隔，单位：秒，比如60秒
	test_interval = 60
	
	#从文件读取要拨测的urls
	with open('urls.txt','r') as f:
		urls = f.readlines()

	urls = [url.strip('\n').strip() for url in urls]
	print(urls)

	# 从文件读取要发送的目标邮箱
	with open('emails.txt','r') as f:
		emails = f.readlines()

	emails = [email.strip('\n').strip() for email in emails]
	print(emails)

	# 使用循环体，让拨测任务持续拨测并触发告警邮件，sleep时间可以设置
	while True:
		
		#异步并行进行web拨测，所有url同时拨测，不需等一个成功后再拨测下一个
		#定义一个循环结构：
		event_loop_test_url = asyncio.get_event_loop()
		

		#耗时测试
		starttime = datetime.datetime.now()
		print('拨测开始时间：',starttime)


		future = banch_test_url(event_loop_test_url,urls)

		tasks_res = event_loop_test_url.run_until_complete(future)

		endtime = datetime.datetime.now()
		print("拨测耗时：%d" %(endtime - starttime).seconds +"s")
		
		

		#把list变成pandas
		df = pd.DataFrame(tasks_res,columns=["DetectTimeStamp","TargetUrls","StatusCode","ElapsedTime"])

		print(time.ctime(),"本次拨测的结果：")
		print(df)

		df = df[df['StatusCode'] != 200]
		# 如果存在拨测不成功的url，则触发自动发送告警邮件
		if len(df.index.values)>0:
			print(time.ctime(),"本次拨测触发自动发送告警邮件！告警信息如下：")
			print(df)
			print('总共有{}个不成功'.format(len(df.index.values)))
			df = df.to_string() #需要转换为字符串
			# df = df.to_html() #需要转换为字符串
			event_loop_auto_sent_mail = asyncio.get_event_loop()
			event_loop_auto_sent_mail.run_until_complete(auto_sent_mail(df,emails))
			# event_loop_auto_sent_mail.close()
		
		time.sleep(test_interval)


