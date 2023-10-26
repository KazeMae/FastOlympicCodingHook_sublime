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
			sttr = tests["url"]
			contest_id = sttr.split("/")
			contest_web = contest_id[2].split(".")
			dirc = ""
			if contest_web[0] == "codeforces" and contest_id[4] == "problem" : # cf problemset
				dirc = self.parsedProblemsFolder + contest_web[0] + "/" + contest_id[5] + "/"
			
			elif contest_web[0] == "codeforces" and contest_id[3] == "gym" : # GYM
				dirc = self.parsedProblemsFolder + contest_id[3] + "/" + contest_id[4] + "/"

			elif contest_web[1] == "acwing" : # Acwing
				dirc = self.parsedProblemsFolder + contest_web[1] + "/"

			elif contest_web[1] == "luogu" : # Luogu
				dirc = self.parsedProblemsFolder + "Luogu/"

			elif contest_web[1] == "nowcoder" : # Nowcoder
				dirc = self.parsedProblemsFolder + contest_web[1] + "/" + contest_id[5] + "/"
				tests["name"] = contest_id[6] + "_" + tests["name"]
			elif contest_web[0] == "vjudge" : # Vjudge
				tid = contest_id[4].split("#")
				dirc = self.parsedProblemsFolder + contest_web[0] + "/" + tid[0] + "/"

			elif contest_web[0] == 'loj' : # LibreOJ
				dirc = self.parsedProblemsFolder + "LibreOJ/p/"

			else :
				dirc = self.parsedProblemsFolder + contest_web[0] + "/"
				if not os.path.exists(dirc):
					os.mkdir(dirc)
				dirc = self.parsedProblemsFolder + contest_web[0] + "/" + contest_id[4] + "/"

			if not os.path.exists(dirc):
				os.mkdir(dirc)
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
		host = 'localhost'
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
