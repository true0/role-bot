from baidusearch.baidusearch import search

try:
    data = search("小米新品", num_results=2)
    for result in data:
        print(result['title'])
        print(result['abstract'])
        print(result['url'])
except Exception as e:
    print(f"搜索失败: {e}")
