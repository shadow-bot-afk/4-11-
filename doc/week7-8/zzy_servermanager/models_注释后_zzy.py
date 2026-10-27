# zzy: 模块功能：servermanager应用的数据模型，定义两张表——
# commands(机器人可执行命令的定义)与EmailSendLog(邮件发送日志记录)
from django.db import models


# Create your models here.
# zzy: 命令表：存储微信机器人可执行的命令定义(标题、命令内容、描述)
class commands(models.Model):
    title = models.CharField('命令标题', max_length=300)
    command = models.CharField('命令', max_length=2000)
    describe = models.CharField('命令描述', max_length=300)
    creation_time = models.DateTimeField('创建时间', auto_now_add=True)
    last_modify_time = models.DateTimeField('修改时间', auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = '命令'
        verbose_name_plural = verbose_name


# zzy: 邮件发送日志表：记录收件人、标题、内容、发送结果，按创建时间倒序
class EmailSendLog(models.Model):
    emailto = models.CharField('收件人', max_length=300)
    title = models.CharField('邮件标题', max_length=2000)
    content = models.TextField('邮件内容')
    send_result = models.BooleanField('结果', default=False)
    creation_time = models.DateTimeField('创建时间', auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = '邮件发送log'
        verbose_name_plural = verbose_name
        ordering = ['-creation_time']
