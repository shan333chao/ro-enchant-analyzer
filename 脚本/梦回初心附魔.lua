import('java.lang.*')
import('java.util.*')
import('com.nx.assist.lua.LuaEngine')
local device = getDevice()
local headers = {}
headers["User-Agent"] = "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3"
local ret = showUI("梦回初心附魔.ui")
local config = jsonLib.decode(ret)
local configHost = config["page0"]["apiHost"]
if configHost == nil or configHost == "" then
    configHost = "http://192.168.5.5:8000"
end
local analyzeUrl = configHost .. "/api/enchantment/analyze?filename="

--[===[验证接口是否可用]===]
local schemesUrl = configHost .. "/api/schemes"
local schemesRet = LuaEngine.httpGet(schemesUrl, headers, 30)
local schemesTab = jsonLib.decode(schemesRet)
if schemesTab == nil or schemesTab["schemes"] == nil or #schemesTab["schemes"] == 0 then
    toast("接口验证失败，请检查服务地址是否正确" , 191 , 334 , 12)
    sleep(3000)
    return
end
toast("接口验证通过，共" .. #schemesTab["schemes"] .. "个方案" , 191 , 334 , 12)
sleep(1000)

local basePath = config["page0"]["basePath"]
if basePath == nil or basePath == "" then
    basePath = "/mnt/sdcard/Screenshots/fumo_pic/"
end

--[===[重新打开附魔界面]===]
function reopenFumo()
	--[===[判断附魔界面是否打开]===]
	local ret = cmpColorEx("1168|28|ce2317,1145|19|bf1812,1128|30|d32615,1146|62|f25413,1148|43|faebe9" , 0.9)
	if ret == 1 then
		--[===[关闭附魔界面]===]
		tap(1147 , 43)
		sleep(500)
	end
	--[===[判断小地图是否打开]===]
	local isMapOpen = cmpColorEx("1241|133|ebebeb,858|132|f3f4f3,928|569|3c6acb,837|570|1a3977" , 0.9)
	if isMapOpen == 0 then
		--[===[打开小地图]===]
		tap(1190 , 103)
		sleep(500)
	end
	--[===[判断NPC 列表是否打开]===]
	local isNpcListOpen = cmpColorEx("695|144|4455aa,725|143|4158aa,764|143|4158aa,790|144|4455aa,597|168|ffe35b,595|281|f9d009,604|345|ffdc33" , 0.9)
	if isNpcListOpen == 0 then
		tap(853 , 132)
		sleep(300)
		tap(746 , 130)
		sleep(300)
	end
	--[===[点击npc 毛小友]===]
	tap(649 , 435)
	sleep(1500)
	--[===[判断附魔入口是否打开]===]
	local isConfirmOpen = cmpColorEx("1198|404|3e59b1,1048|402|3e5bb2,1107|475|ffffff,1189|469|455eb0,1119|416|3c54aa" , 0.9)
	if isConfirmOpen == 1 then
		tap(1081 , 399)
		sleep(500)
	end
end

local isFumoOpen = cmpColorEx("275|657|fdb320,454|657|fe9e17,857|665|fe981c,1019|654|febb22" , 0.9)
if isFumoOpen == 0 then
	reopenFumo()
end

-- 无限 while 循环 + 时间戳作为文件名
while true do
	local isReady = cmpColorEx("480|38|82a3d3,245|37|82a3d3,252|37|fcfcfc,423|665|ff991c,286|664|ff991c" , 0.9)
	
	if isReady == 1 then
		
		-- 用系统时间戳做文件名（永远不重复）
		local timestamp = os.time()
		local filename = "fumo_" ..device .. timestamp .. ".png"
		local filePath = basePath .. filename
		
		snapShot(filePath , 116 , 67 , 616 , 251)
		
		local urlGet = analyzeUrl .. filename
		print(urlGet)
		local getRet = LuaEngine.httpGet(urlGet , headers , 30)
		local tab = jsonLib.decode(getRet)
		print(tab)
		if tab == nil then
			toast("接口异常请排查是否启动识别服务" , 191 , 334 , 12)
			sleep(2000)
			break
		end
		if tab["status"] == - 1 then
			toast("接口异常请排查是否启动识别服务" , 191 , 334 , 12)
			sleep(2000)
			break
		end
		if tab["status"] == 1 then
			tap(375 , 661)
			toast("附魔完成" , 191 , 334 , 12)
			sleep(2000)
			break
		end
		
		local isConfirm = cmpColorEx("703|464|45a70c,457|463|415cb2,573|460|415fb2,847|464|45a70c,637|462|ffffff" , 0.9)
		if isConfirm == 1 then
			tap(758 , 462)
			sleep(1000)
		end
	end
	tap(942 , 667)
	sleep(1000)
	local seed = 0
	while true do
		--[===[判断是否重新附魔按钮可用如果不可用等待200毫秒]===]
		local ret = cmpColorEx("1001|666|ff991c,850|652|ffc320,941|643|ffd61c,911|660|ffffff,997|659|ff9d18" , 0.9)
		if ret == 0 then
			sleep(200)
			seed = seed + 1
			if seed > 30 then
				reopenFumo()
				toast("附魔卡住了" , 191 , 334 , 12)
				sleep(500)
				break
			end
		else
			break
		end
	end
end
