import io, os, sqlite3, zipfile
from datetime import date, datetime
from functools import wraps
from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from PIL import Image
from pypdf import PdfReader, PdfWriter
import qrcode

TOOLS = {
 "image-to-pdf": {"name":"تحويل الصور إلى PDF", "category":"الصور", "icon":"▧", "description":"حوّل صورك إلى ملف PDF مرتب."},
 "image-compressor": {"name":"ضغط الصور", "category":"الصور", "icon":"◒", "description":"قلّل الحجم مع الحفاظ على الجودة."},
 "image-resizer": {"name":"تغيير حجم الصور", "category":"الصور", "icon":"↔", "description":"اضبط أبعاد صورك بدقة."},
 "pdf-merge": {"name":"دمج ملفات PDF", "category":"PDF", "icon":"⊞", "description":"اجمع ملفات PDF في مستند واحد."},
 "pdf-split": {"name":"تقسيم ملفات PDF", "category":"PDF", "icon":"÷", "description":"استخرج الصفحات التي تحتاجها."},
 "qr-generator": {"name":"إنشاء QR Code", "category":"متنوعة", "icon":"▦", "description":"أنشئ رمز QR قابلًا للتنزيل."},
 "percentage-calculator": {"name":"حساب النسبة المئوية", "category":"الحسابات", "icon":"%", "description":"احسب النسب بسرعة ووضوح."},
 "age-calculator": {"name":"حساب العمر", "category":"الحسابات", "icon":"◷", "description":"اعرف عمرك بالسنوات والأشهر."}
 ,"cv-builder": {"name":"منشئ السيرة الذاتية", "category":"متنوعة", "icon":"▤", "description":"أنشئ سيرة ذاتية احترافية جاهزة للطباعة والمشاركة خلال دقائق."}
}
PREMIUM = ["معالجة ملفات كثيرة دفعة واحدة", "ضغط PDF المتقدم", "تحويل PDF إلى Word", "تحويل PDF إلى Excel", "إزالة خلفية الصور بالذكاء الاصطناعي", "تحسين الصور بالذكاء الاصطناعي", "استخراج النص من الصور OCR", "الكتابة والتلخيص بالذكاء الاصطناعي", "قوالب سيرة ذاتية احترافية إضافية"]

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "development-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
app.config["DATABASE"] = os.path.join(app.instance_path, "adawaty.sqlite3")
os.makedirs(app.instance_path, exist_ok=True)

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db: db.close()
def init_db():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, created_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS favorites (
        user_id INTEGER NOT NULL, tool_slug TEXT NOT NULL,
        PRIMARY KEY (user_id, tool_slug), FOREIGN KEY(user_id) REFERENCES users(id))""")
    db.commit()
@app.before_request
def load_user():
    init_db()
    g.user = get_db().execute("SELECT id,name,email,created_at FROM users WHERE id=?", (session.get("user_id"),)).fetchone() if session.get("user_id") else None
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash("سجّل الدخول أولًا للوصول إلى حسابك.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def files(): return [f for f in request.files.getlist("files") if f and f.filename]
def image_file(f):
    if not f or f.mimetype not in ("image/jpeg","image/png","image/webp"): abort(400, "صيغة الصورة غير مدعومة")
def pdf_file(f):
    if not f or f.mimetype != "application/pdf": abort(400, "يرجى اختيار ملف PDF")
def download(data, name, mimetype):
    return send_file(io.BytesIO(data), as_attachment=True, download_name=name, mimetype=mimetype)

@app.context_processor
def globals(): return {"tools": TOOLS, "premium": PREMIUM, "year": datetime.now().year, "current_user": getattr(g, "user", None)}

@app.route("/")
def home(): return render_template("home.html", title="أدواتي | أدوات عربية سريعة", description="أدوات عربية بسيطة وسريعة لإنجاز مهامك اليومية بدون تعقيد.")
@app.route("/tools")
def tools_page(): return render_template("tools.html", title="كل الأدوات | أدواتي", description="اكتشف أدواتي المجانية للصور وPDF والحسابات.")
@app.route("/tools/<slug>")
def tool_page(slug):
    tool = TOOLS.get(slug)
    if not tool: abort(404)
    return render_template("tool.html", tool=tool, slug=slug, title=f"{tool['name']} | أدواتي", description=tool["description"])
@app.route("/premium")
def premium_page(): return render_template("premium.html", title="الأدوات الاحترافية | أدواتي", description="أدوات احترافية متقدمة قادمة قريبًا.")
@app.route("/about")
def about(): return render_template("page.html", heading="من نحن", body="أدواتي منصة عربية عملية نبنيها لتقليل الوقت بين فكرتك والنتيجة. نركز على أدوات واضحة، سريعة، وتحترم خصوصية ملفاتك.")
@app.route("/contact")
def contact(): return render_template("page.html", heading="تواصل معنا", body="للاقتراحات والدعم، راسلنا على support@adawaty.example. نقرأ كل رسالة ونستخدم ملاحظاتكم لتحسين الأدوات.")
@app.route("/faq")
def faq(): return render_template("faq.html", title="الأسئلة الشائعة | أدواتي", description="إجابات عن استخدام أدواتي وخصوصية الملفات.")
@app.route("/privacy")
def privacy(): return render_template("page.html", heading="سياسة الخصوصية", body="تُعالج ملفات الأدوات المجانية في الذاكرة ولا نحتفظ بها بعد تجهيز النتيجة. لا نبيع بياناتك أو نعرض محتوى ملفاتك لأي طرف.")
@app.route("/terms")
def terms(): return render_template("page.html", heading="شروط الاستخدام", body="استخدم أدواتي للملفات التي تملك حق استخدامها. الخدمة مقدمة كما هي، ونحتفظ بحق تطوير الأدوات وإتاحة خدمات احترافية مستقبلًا.")
@app.route("/blog")
def blog(): return render_template("blog.html", title="مدونة أدواتي", description="إرشادات سريعة للصور وملفات PDF.")
@app.route("/robots.txt")
def robots(): return app.send_static_file("robots.txt")
@app.route("/sitemap.xml")
def sitemap(): return app.send_static_file("sitemap.xml")
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user: return redirect(url_for("dashboard"))
    if request.method == "POST":
        name=request.form.get("name", "").strip(); email=request.form.get("email", "").strip().lower(); password=request.form.get("password", "")
        if len(name)<2 or "@" not in email or len(password)<8: flash("أدخل اسمًا صحيحًا وبريدًا صالحًا وكلمة مرور من 8 أحرف على الأقل.", "error")
        else:
            try:
                db=get_db(); cur=db.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(name,email,generate_password_hash(password),datetime.utcnow().isoformat()));db.commit();session.clear();session["user_id"]=cur.lastrowid;flash("تم إنشاء حسابك بنجاح.","success");return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError: flash("هذا البريد مسجل بالفعل. جرّب تسجيل الدخول.", "error")
    return render_template("account.html", mode="signup", title="إنشاء حساب | أدواتي")
@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user: return redirect(url_for("dashboard"))
    if request.method == "POST":
        user=get_db().execute("SELECT * FROM users WHERE email=?",(request.form.get("email", "").strip().lower(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear(); session["user_id"]=user["id"]; flash("أهلًا بعودتك.", "success"); return redirect(url_for("dashboard"))
        flash("البريد الإلكتروني أو كلمة المرور غير صحيحة.", "error")
    return render_template("account.html", mode="login", title="دخول | أدواتي")
@app.post("/logout")
def logout(): session.clear(); flash("تم تسجيل الخروج.", "success"); return redirect(url_for("home"))
@app.route("/dashboard")
@login_required
def dashboard():
    favs=get_db().execute("SELECT tool_slug FROM favorites WHERE user_id=?",(g.user["id"],)).fetchall()
    return render_template("dashboard.html", favorites=[TOOLS[x["tool_slug"]] | {"slug":x["tool_slug"]} for x in favs if x["tool_slug"] in TOOLS], title="لوحة التحكم | أدواتي")
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name=request.form.get("name", "").strip()
        if len(name)<2: flash("الاسم قصير جدًا.", "error")
        else: get_db().execute("UPDATE users SET name=? WHERE id=?",(name,g.user["id"]));get_db().commit();flash("تم حفظ بياناتك.", "success");return redirect(url_for("profile"))
    return render_template("profile.html", title="الملف الشخصي | أدواتي")
@app.post("/api/favorites/<slug>")
@login_required
def favorite(slug):
    if slug not in TOOLS: abort(404)
    db=get_db(); old=db.execute("SELECT 1 FROM favorites WHERE user_id=? AND tool_slug=?",(g.user["id"],slug)).fetchone()
    if old: db.execute("DELETE FROM favorites WHERE user_id=? AND tool_slug=?",(g.user["id"],slug)); saved=False
    else: db.execute("INSERT INTO favorites(user_id,tool_slug) VALUES(?,?)",(g.user["id"],slug)); saved=True
    db.commit(); return jsonify(saved=saved)

@app.post("/api/image-compressor")
def compress():
    uploaded=files()
    if len(uploaded)!=1: abort(400,"اختر صورة واحدة للضغط")
    f=uploaded[0]; image_file(f); raw=f.read(); im=Image.open(io.BytesIO(raw)).convert("RGB"); quality=max(30,min(95,int(request.form.get("quality",75)))); out=io.BytesIO(); im.save(out,"JPEG",quality=quality,optimize=True); data=out.getvalue(); r=download(data,"compressed.jpg","image/jpeg"); r.headers["X-Before-Size"]=str(len(raw)); r.headers["X-After-Size"]=str(len(data)); return r
@app.post("/api/image-resizer")
def resize():
    uploaded=files()
    if len(uploaded)!=1: abort(400,"اختر صورة واحدة")
    f=uploaded[0]; image_file(f); im=Image.open(f.stream); w=int(request.form.get("width") or im.width); h=int(request.form.get("height") or im.height)
    if not 1<=w<=10000 or not 1<=h<=10000: abort(400,"الأبعاد المسموحة من 1 إلى 10000 بكسل")
    im=im.resize((w,h),Image.Resampling.LANCZOS); out=io.BytesIO(); im.convert("RGB").save(out,"JPEG",quality=90); return download(out.getvalue(),"resized.jpg","image/jpeg")
@app.post("/api/image-to-pdf")
def to_pdf():
    ims=[]
    for f in files(): image_file(f); ims.append(Image.open(f.stream).convert("RGB"))
    if not ims: abort(400,"اختر صورة واحدة على الأقل")
    out=io.BytesIO(); ims[0].save(out,"PDF",save_all=True,append_images=ims[1:]); return download(out.getvalue(),"images.pdf","application/pdf")
@app.post("/api/pdf-merge")
def merge():
    writer=PdfWriter()
    uploaded=files()
    if len(uploaded)<2: abort(400,"اختر ملفي PDF على الأقل للدمج")
    for f in uploaded: pdf_file(f); writer.append(f.stream)
    out=io.BytesIO(); writer.write(out); return download(out.getvalue(),"merged.pdf","application/pdf")
@app.post("/api/pdf-split")
def split():
    uploaded=files()
    if len(uploaded)!=1: abort(400,"اختر ملف PDF واحدًا")
    f=uploaded[0]; pdf_file(f); reader=PdfReader(f.stream); raw=request.form.get("pages","").strip(); wanted=[]
    if not raw: abort(400,"أدخل أرقام الصفحات المطلوب استخراجها")
    for token in raw.split(","):
        try:
            n=int(token.strip())-1
            if 0<=n<len(reader.pages): wanted.append(n)
        except ValueError: pass
    if not wanted: abort(400,"أدخل أرقام صفحات صحيحة ضمن الملف")
    if len(wanted)==1:
        w=PdfWriter();w.add_page(reader.pages[wanted[0]]);out=io.BytesIO();w.write(out);return download(out.getvalue(),"page.pdf","application/pdf")
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for n in wanted:
            w=PdfWriter();w.add_page(reader.pages[n]);p=io.BytesIO();w.write(p);z.writestr(f"page-{n+1}.pdf",p.getvalue())
    return download(out.getvalue(),"pages.zip","application/zip")
@app.post("/api/qr-generator")
def qr():
    value=request.form.get("value","").strip()
    if not value: abort(400,"أدخل نصًا أو رابطًا")
    out=io.BytesIO();qrcode.make(value).save(out,"PNG");return download(out.getvalue(),"qrcode.png","image/png")

@app.errorhandler(413)
def too_large(e): return jsonify(error="حجم الملف أكبر من الحد المسموح."),413
@app.errorhandler(400)
def bad_request(e):
    if request.path.startswith("/api/"): return jsonify(error=e.description),400
    return render_template("page.html",heading="تعذر تنفيذ الطلب",body=e.description),400
@app.errorhandler(404)
def not_found(e): return render_template("page.html",heading="الصفحة غير موجودة",body="الرابط الذي طلبته غير متاح. يمكنك العودة إلى الأدوات."),404

if __name__ == "__main__": app.run()
