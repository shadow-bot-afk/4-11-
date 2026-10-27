# 组员3：comments 应用模块代码质量分析报告

## 一、负责模块源码文件清单及分析范围说明
- **负责目录**：`src/comments/`
- **核心文件清单**：`models.py`（数据模型）、`views.py`（视图逻辑）、`utils.py`（工具函数）
- **分析范围**：本次仅分析修改 comments 模块的实际运行代码，未涉及其他模块。

## 二、人工代码质量分析结果
在阅读源码过程中，发现以下问题：
1. **问题描述**：在 `views.py` 的 `CommentPostView.form_valid` 中，存在多余的数据库查询。
   - **位置**：`comments/views.py`，`form_valid` 方法。
   - **原代码**：`author = BlogUser.objects.get(pk=user.pk)`
   - **处理方案**：既然 `self.request.user` 已经是当前用户实例，直接使用 `author = user` 即可，减少数据库开销。**已修复**。
2. **问题描述**：`views.py` 中获取父评论时直接使用 `.get()`，若前端传入不存在的 ID，会引发 `DoesNotExist` 异常导致 500 报错。
   - **处理方案**：建议后续改用 `get_object_or_404()`。（本次暂未修复，记录以便后续优化）。

## 三、工具质量分析结果
- **使用工具**：Flake8
- **检查方式**：在终端运行 `flake8 comments/ --max-line-length=120`
- **主要结果**：发现大量行尾空白（W291）、多余空行（W293）、文件末尾缺少换行（W292）及导入未使用（F401）等问题。
- **代表性问题截图**：
  ![工具截图](images/tool-flake8.png)

## 四、源码修改与验证记录
- **修改文件**：`comments/views.py`、`comments/models.py`（添加了 `#gys:` 注释并修复格式问题）
- **修改内容**：移除了重复的 `BlogUser.objects.get()` 查询；清理了行尾多余空格；在文件末尾补充了换行。
- **验证方式**：启动 `python manage.py runserver`，进入博客前台，点击文章并发表评论，评论正常显示，功能正常。

## 五、个人注释统计
- 注释文件数：2 个（`models.py`, `views.py`）
- 注释行数：约 25 行
- 标识缩写：`#gys:`