import sublime
import sublime_plugin
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import _thread
import threading
import platform
import os
import re
import time

def decodeStringsOfFile(s):
	L = ["<", ">", "/", "\\", "|", ":", "\"", "*", "?", ".", "\'"]
	if platform.system() != "Windows":
		L.append("(")
		L.append(")")
		L.append("@")
		L.append("#")
		L.append("$")
		L.append("&")
		L.append("%")
	for i in L:
		s = s.replace(i, "")
	s = re.sub('[^\x00-\xFF\u4e00-\u9fa5]', '', s)
	return s

def MakeHandlerClassFromFilename():
	class HandleRequests(BaseHTTPRequestHandler):
		def newFile(self, tests):
			web_url = tests["url"]
			dirc = ''
			if 'codeforces.com' in web_url:     # CodeForces
				web_url = web_url.split("codeforces.com/")[1].split('/')

				if web_url[0] == 'problemset':  # Problemset
					dirc = 'Codeforces/' + web_url[2]

				elif web_url[0] == 'contest':   # Contest
					dirc = 'Codeforces/' + web_url[1]

				elif web_url[0] == 'gym':       # Gym
					dirc = 'GYM/' + web_url[1]

			elif 'atcoder.jp' in web_url:       # Atcoder
				web_url = web_url.split("atcoder.jp/")[1].split('/')
				dirc = 'AtCoder/' + web_url[1]

			elif 'acwing.com' in web_url:       # Acwing 未适配竞赛
				web_url = web_url.split("acwing.com/")[1].split('/')
				dirc = 'Acwing/' + web_url[-2]

			elif 'luogu.com.cn' in web_url:     # Luogu
				web_url = web_url.split("luogu.com.cn/")[1].split('/')

				if 'contestId' in web_url[-1]:  # Contest
					dirc = 'Luogu/' + web_url[-1].split('contestId=')[-1] + '/' + web_url[-1].split('?')[0]
				else:
					dirc = 'Luogu/' + web_url[-1]

			elif 'ac.nowcoder.com' in web_url:
				web_url = web_url.split("ac.nowcoder.com/")[1].split('/')
				if web_url[1] == 'contest':
					dirc = 'NowCoder/' + web_url[2]
					tests["name"] = web_url[3] + '_' + tests["name"]
				else:
					dirc = 'NowCoder'

			elif 'vjudge.net' in web_url:
				web_url = web_url.split("vjudge.net/")[1].split('/')
				if web_url[0] == 'contest':
					dirc = 'Vjudge/' + web_url[1].split('#')[0]
				else:
					dirc = 'Vjudge'
			elif 'hdu.edu.cn' in web_url:
				web_url = web_url.split("hdu.edu.cn/")[1].split('/')
				if web_url[0] == 'contest':
					dirc = 'HDOJ/' + web_url[-1].split('&')[0].split('cid=')[1]
					tests["name"] = web_url[-1].split('&')[1].split('pid=')[-1] + '.' + tests["name"]
				else:
					dirc = 'HDOJ'
			else:
				dirc = tests["group"]

			dirc = self.parsedProblemsFolder + dirc + '/'

			if not os.path.exists(dirc):
				os.mkdir(dirc)
			print(dirc)
			fn = dirc + decodeStringsOfFile(tests["name"].replace(" ", "_")) + '.' + self.settings.get("file-suffix", "cpp")
			fl_size = -1
			if not os.path.exists(fn):
				cppF = open(fn, "w", encoding = "utf-8")
				code = (self.templ
					.replace("%$Problem$%" , tests["name"])
					.replace("%$Contest$%" , tests["group"])
					.replace("%$URL$%"   , tests["url"])
					.replace("%$Time$%" , time.strftime(self.settings.get("time-format", "%Y-%m-%d %H:%M:%S"), time.localtime()))
					.replace("%$MemoryL$%" , str(tests["memoryLimit"]))
					.replace("%$TimeL$%"   , str(tests["timeLimit"])))
				cppF.write(code)
				fl_size = len(code)
				cppF.close()
			else:
				fl_size = os.path.getsize(fn)
			vw = sublime.active_window().open_file(fn)
			while vw.is_loading() == True:
				pass
			vw.show(fl_size, animate = False)
			tests = tests["tests"]
			ntests = []
			for test in tests:
				ntest = {
					"test": test["input"],
					"correct_answers": [test["output"].strip()]
				}
				ntests.append(ntest)
			nfilename = fn + ":tests"
			if platform.system() == "Windows":
				nfilename = fn + "__tests"
			with open(nfilename, "w") as f:
				f.write(json.dumps(ntests))
		def do_POST(self):
			print("POST received.")
			try:
				content_length = int(self.headers['Content-Length'])
				body = self.rfile.read(content_length)
				J = json.loads(body.decode('utf8'))
				self.settings = sublime.load_settings("FastOlympicCodingHook.sublime-settings")
				self.templateFile = self.settings.get("template-file")
				self.parsedProblemsFolder = self.settings.get("parse-folder")
				# print("Received ->", body)
				g = open(self.templateFile, "r", encoding = "utf-8")
				self.templ = g.read()
				g.close()
				if(type(J).__name__ == "array"):
					for i in range(len(J)):
						self.newFile(J[i])
				else:
					self.newFile(J)
			except Exception as e:
				print("Error handling POST - " + str(e))
			self.send_response(202)
			self.send_header("pragma", "no-cache")
			self.send_header("connection", "close")
			self.send_header("Strict-Transport-Security", "max-age=0")
			self.end_headers()
			return
	return HandleRequests


class CompetitiveCompanionServer:
	def startServer():
		host = ''
		settings = sublime.load_settings("FastOlympicCodingHook.sublime-settings")
		port = settings.get("server-port", 12345)
		HandlerClass = MakeHandlerClassFromFilename()
		global httpd
		httpd = HTTPServer((host, port), HandlerClass)
		httpd.allow_reuse_address = True
		print("Start server... - ::" + str(port))
		httpd.serve_forever()
		print("Server has been shutdown")

try:
	_thread.start_new_thread(CompetitiveCompanionServer.startServer,())
except Exception as e:
	print("Error: unable to start thread - " + str(e))
