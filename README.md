# Binance Auto Trader Bot

بوت تداول آلي حقيقي للعملات الرقمية على Binance مع إشعارات Telegram.

## كيفية الاستخدام

1. أنشئ API Key وSecret من حساب Binance الخاص بك (صلاحيات Spot Trading فقط).
2. أدخل مفاتيح API وتوكن Telegram ومعرف الدردشة في ملف `config.py`.
3. ثبت المكتبات:
pip install -r requirements.txt
4. شغّل البوت محليًا أو على Render (Background Worker مدفوع).

## ملاحظات

- يستخدم استراتيجية زخم و حجم تداول.
- يفتح صفقات بنسبة 10% من الرصيد المتاح.
- وقف خسارة 3%، جني ربح 7%.
- أقصى 3 صفقات متزامنة.
- يرسل تنبيهات إلى Telegram.
