# أدواتي | Adawaty

منصة عربية RTL للأدوات اليومية. تعمل الأدوات المجانية محلياً ولا تحتاج إلى حساب.

## التشغيل

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app backend.app run
```

افتح `http://127.0.0.1:5000`.

## ملاحظات النشر

- اضبط `FLASK_SECRET_KEY` وقيمة `MAX_UPLOAD_MB` في متغيرات البيئة.
- ترفع الملفات إلى مجلد مؤقت وتحذف مباشرة بعد تجهيز التنزيل.
- أدوات الذكاء الاصطناعي مدفوعة ومهيأة لربط مزود API مستقبلاً عبر `OPENAI_API_KEY` فقط من الخادم.
