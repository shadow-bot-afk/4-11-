from django.contrib.auth.forms import forms
from django.forms import widgets


class RequireEmailForm(forms.Form):
    # sw: 第三方登录补填邮箱表单
    email = forms.EmailField(label='电子邮箱', required=True)
    oauthid = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        # sw: 初始化表单，设置邮箱输入框占位文字和样式类
        super(RequireEmailForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget = widgets.EmailInput(
            attrs={'placeholder': "email", "class": "form-control"})
