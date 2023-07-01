from flask import Flask, render_template, redirect, session, request
from werkzeug.security import generate_password_hash as gph
from werkzeug.security import check_password_hash as cph
from werkzeug.utils import secure_filename
from datetime import timedelta
from sklearn.ensemble import GradientBoostingRegressor as GBR
from sklearn.ensemble import GradientBoostingClassifier as GBC
import statsmodels.api as sm
import pandas as pd
import sqlite3
import html
import secrets

ALLOWED_EXTENSIONS = {"csv"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = "test"
app.permanent_session_lifetime = timedelta(minutes=60)

@app.route("/")
def route():
    return redirect("login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method=="GET":
        if request.args.get("msg") is not None:
            return render_template("login.html", 
                                   msg=html.escape(request.args.get("msg")))
        else:
            return render_template("login.html")
    elif request.method=="POST":
        email = request.form["email"]
        passwd = request.form["password"]
        con = sqlite3.connect("data.db")
        cur = con.cursor()
        cur.execute("""
                    SELECT name, email, password 
                    FROM USERS 
                    WHERE email=?
                    """,
                    (email,))
        name = []
        email = []
        hashpass = []
        for row in cur:
            name.append(row[0])
            email.append(row[1])
            hashpass.append(row[2])
        if len(hashpass) == 0:
            return redirect("login?msg=メールアドレスが間違っています")
        if cph(hashpass[0], passwd):
            session["name"] = name[0]
            session["email"] = email[0]
            return redirect("home")
        else:
            return redirect("login?msg=パスワードが間違っています")
        
@app.route("/signup", methods=["GET", "POST"])
def singup():
    if request.method=="GET":
        if request.args.get("msg") is not None:
            return render_template("singup.html", 
                                   msg=html.escape(request.args.get("msg")))
        else:
            return render_template("signup.html")
    elif request.method=="POST":
        name = request.form["name"]
        email = request.form["email"]
        passwd = request.form["password"]
        passwt = request.form["passwordtmp"]
        con = sqlite3.connect("data.db")
        cur = con.cursor()
        cur.execute("""
                    SELECT * FROM USERS where email=?
                    """,
                    (email,))
        tmp = []
        for row in cur:
            tmp.append(row)
        if len(tmp)!=0:
            return render_template("signup?msg=ユーザが既にいます")
        if passwd != passwt:
            return render_template("signup?msg=パスワードが間違っています")
        con.close()
        con = sqlite3.connect("data.db")
        cur = con.cursor()
        cur.execute("""
                    INSERT INTO USERS(name, email, password) VALUES (?, ?, ?)
                    """,
                    (name, email, gph(passwd)))
        con.commit()
        con.close()
        session["name"] = name
        session["email"] = email
        return redirect("home")
    
@app.route("/home")
def home():
    if "name" in session:
        token = secrets.token_hex()
        session["home"] = token
        print(session["name"])
        return render_template("home.html", 
                               name=html.escape(session["name"]), 
                               homeCSRF=token)
    else:
        return redirect("login.html")

@app.route("/table", methods=["GET", "POST"])
def table():
    if "name" in session:
        if request.form["homeCSRF"] == session["home"]:
            if "file" not in request.files:
                return "ファイルは送信されていません"
            file = request.files["file"]
            if file.filename == "":
                return "ファイル名が有りません"
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(filename)
                df = pd.read_csv(filename, encoding="shift-jis")
                columns = df.columns
                values = df.values
                token = secrets.token_hex()
                session["table"] = token
                res = "<a href=\"home\">ホームに戻る</a><form action=\"result\" method=\"POST\">\n"
                res = res + "<input type=\"radio\" value=\"reg\" name=\"yset\" checked>回帰<br>\n"
                res = res + "<input type=\"radio\" value=\"cla\" name=\"yset\">分類<br>\n"
                res = res + "<input type=\"hidden\" name=\"tableCSRF\" value=\"" + html.escape(token) + "\">"
                res = res + "<input type=\"hidden\" name=\"filename\" value=\"" + html.escape(filename) + "\">"
                res = res + "<input type=\"submit\" value=\"分析\">"
                res = res + "<table border=\"1\">\n"
                res = res + "\t<tr>"
                count = 0
                for col in columns:
                    if count == 0:
                        res = res + "<th><input type=\"radio\" value=\"" + html.escape(col) + "\" name=\"y\" checked>目的変数<br><input type=\"checkbox\" name=\"dum\" value=\"" + html.escape(col) + "\">ダミー変数<br>" + html.escape(col) + "</th>"
                        count = count + 1
                    else:
                        res = res + "<th><input type=\"radio\" value=\"" + html.escape(col) + "\" name=\"y\">目的変数<br><input type=\"checkbox\" name=\"dum\" value=\"" + html.escape(col) + "\">ダミー変数<br>" + html.escape(col) + "</th>"
                res = res + "</tr>\n"
                for val in values:
                    res = res + "<tr>"
                    for i in range(len(val)):
                        res = res + "<td>" + html.escape(str(val[i])) + "</td>"
                    res = res + "</tr>"
                return res
        else:
            return redirect("home?msg=正規のアクセスをしてください")
    else:
        return redirect("login.html")

@app.route("/result", methods=["GET", "POST"])
def result():
    if "name" in session:
        if request.form["tableCSRF"] == session["table"]:
            try:
                res = "<a href=\"home\">ホームに戻る</a><br><h1>分析結果</h1>\n"
                df = pd.read_csv(request.form["filename"], encoding="shift-jis")
                if len(request.form.getlist("dum")) != 0:
                    dumcol = []
                    for col in request.form.getlist("dum"):
                        dumcol.append(col)
                    df = pd.get_dummies(df, columns=dumcol)
                X = sm.add_constant(df.drop(request.form["y"], axis=1))
                if request.form["yset"]=="cla":
                    res = res + "<h2>ロジスティック回帰</h2>"
                    y_set = list(set(df[request.form["y"]].values))
                    for i in range(len(y_set)):
                        try:
                            a = int(y_set[i])
                            a = a + 1
                        except:
                            return "<a href=\"home\">ホーム</a><br><h2>目的変数も数値にしてください。</h2>"
                    if len(y_set) > 2:
                        model = sm.MNLogit(df[request.form["y"]], X).fit_regularized()
                        res = res + "<pre>" + html.escape(str(model.summary())) + "</pre>"
                        model = GBC()
                        model.fit(df.drop(request.form["y"], axis=1), df[request.form["y"]])
                        imp = model.feature_importances_
                        x = df.drop(request.form["y"], axis=1)
                        res = res + "<h2>分類寄与率</h2>"
                        res = res + "<table>\n"
                        for i in range(len(imp)):
                            res = res + "\t<tr><td>" + html.escape(str(x.columns[i])) + "</td><td>" + html.escape(str(imp[i])) + "</td></tr>\n"
                        res = res + "</table>"
                        return res
                    else:
                        model = sm.Logit(df[request.form["y"]], X).fit_regularized()
                        res = res + "<pre>" + html.escape(str(model.summary())) + "</pre>"
                        model = GBC()
                        model.fit(df.drop(request.form["y"], axis=1), df[request.form["y"]])
                        imp = model.feature_importances_
                        x = df.drop(request.form["y"], axis=1)
                        res = res + "<h2>分類寄与率</h2>"
                        res = res + "<table>\n"
                        for i in range(len(imp)):
                            res = res + "\t<tr><td>" + html.escape(str(x.columns[i])) + "</td><td>" + html.escape(str(imp[i])) + "</td></tr>\n"
                        res = res + "</table>"
                        return res
                elif request.form["yset"]=="reg":
                    res = res + "<h2>重回帰分析</h2>"
                    model = sm.OLS(df[request.form["y"]], X).fit()
                    res = res + "<pre>" + html.escape(str(model.summary())) + "</pre>"
                    model = GBR()
                    model.fit(df.drop(request.form["y"], axis=1), df[request.form["y"]])
                    imp = model.feature_importances_
                    x = df.drop(request.form["y"], axis=1)
                    res = res + "<h2>回帰寄与率</h2>"
                    res = res + "<table>\n"
                    for i in range(len(imp)):
                        res = res + "\t<tr><td>" + html.escape(str(x.columns[i])) + "</td><td>" + html.escape(str(imp[i])) + "</td></tr>\n"
                    res = res + "</table>"
                    return res
            except:
                return "<a href=\"home\">ホーム</a><br><h2>前画面で操作ミスです。</h2>"
    else:
        return redirect("login.html")


if __name__ == "__main__":
    app.run()
