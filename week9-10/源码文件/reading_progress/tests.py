from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from reading_progress.models import ArticleReadProgress

User = get_user_model()

# sw：阅读进度后端接口单元测试
class ReadProgressTestCase(TestCase):
    def setUp(self):
        # sw：每次测试前，创建测试用户并且登录
        self.client = Client()
        self.test_user = User.objects.create_user(username="testsw", password="123456")
        self.client.login(username="testsw", password="123456")

    def test_save_progress(self):
        # sw：测试提交阅读进度，存入数据库
        res = self.client.post("/api/reading-progress/", {
            "article_id": 1,
            "progress": 0.65
        })
        self.assertEqual(res.status_code, 200)
        obj = ArticleReadProgress.objects.get(user=self.test_user, article_id=1)
        self.assertEqual(obj.progress, 0.65)

    def test_get_progress(self):
        # sw：测试读取已保存的进度
        ArticleReadProgress.objects.create(user=self.test_user, article_id=2, progress=0.33)
        res = self.client.get("/api/reading-progress/?article_id=2")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["progress"], 0.33)

    def test_visitor_no_save(self):
        # sw：退出登录，游客不能保存进度
        self.client.logout()
        res = self.client.post("/api/reading-progress/", {
            "article_id": 1,
            "progress": 0.8
        })
        # 游客请求我们后端可以返回成功但是不入库
        self.assertEqual(ArticleReadProgress.objects.filter(article_id=1).count(), 0)