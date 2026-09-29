import json

with open('blog_fixture.json', encoding='utf-8') as f:
    data = json.load(f)

order = {'blog.category': 0, 'blog.tag': 1, 'blog.article': 3}
data.sort(key=lambda o: order.get(o['model'], 2))

with open('blog_fixture_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('搞定，生成了 blog_fixture_fixed.json')