import os
import smtplib


def sending_mail(name, email, phone, message):
    my_mail = os.environ.get('MY_MAIL')
    password = os.environ.get('PASSWORD')
    with smtplib.SMTP("smtp.gmail.com") as connect:
        connect.starttls()
        connect.login(user=my_mail, password=password)
        connect.sendmail(
            from_addr=my_mail,
            to_addrs="dpoulomi58@yahoo.com",
            msg=f"Subject:Website Mail\n\n Name:{name}\n"
                f"Email:{email}\n"
                f"Phone No:{phone}\n"
                f"Message:{message}"
        )