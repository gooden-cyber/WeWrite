# 项目功能优化方向

## 一、微信公众号发布功能优化

### 当前问题

1. **发布流程复杂**：预览 → 确认 → 发布，步骤多
2. **无草稿管理**：发布后无法撤回或修改
3. **无定时发布**：只能立即发布或每天自动发布
4. **无发布历史**：无法查看已发布内容

### 优化方案

#### 1. 草稿箱功能

```python
# 新增 API
@app.post("/api/draft/save")
async def save_draft(article_id: str, content: str):
    """保存草稿"""
    draft_dir = PROJECT_ROOT / "knowledge" / "wechat" / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    
    draft = {
        "article_id": article_id,
        "content": content,
        "saved_at": datetime.now().isoformat(),
        "status": "draft"
    }
    
    draft_file = draft_dir / f"{article_id}.json"
    draft_file.write_text(json.dumps(draft, ensure_ascii=False, indent=2))
    
    return {"success": True, "draft_id": article_id}

@app.get("/api/drafts")
async def list_drafts():
    """获取草稿列表"""
    # ...
```

#### 2. 定时发布功能

```python
@app.post("/api/publish/schedule")
async def schedule_publish(request: Request):
    """定时发布"""
    body = await request.json()
    article_id = body.get("article_id")
    publish_at = body.get("publish_at")  # ISO 格式时间
    
    # 保存到定时发布队列
    schedule_file = PROJECT_ROOT / "knowledge" / "wechat" / "schedule.jsonl"
    record = {
        "article_id": article_id,
        "publish_at": publish_at,
        "created_at": datetime.now().isoformat(),
        "status": "pending"
    }
    
    with open(schedule_file, "a") as f:
        f.write(json.dumps(record) + "\n")
    
    return {"success": True, "message": f"已设置定时发布：{publish_at}"}
```

#### 3. 发布历史管理

```python
@app.get("/api/publish/history")
async def publish_history(limit: int = 20):
    """获取发布历史"""
    history_file = PROJECT_ROOT / "knowledge" / "wechat" / "publish_history.jsonl"
    
    if not history_file.exists():
        return {"history": []}
    
    lines = history_file.read_text().strip().split("\n")
    records = [json.loads(line) for line in reversed(lines) if line.strip()]
    
    return {"history": records[:limit]}
```

#### 4. 微信素材管理

```python
@app.get("/api/wechat/materials")
async def list_wechat_materials():
    """获取微信素材列表"""
    # 调用微信 API 获取已上传素材
    # ...

@app.delete("/api/wechat/materials/{media_id}")
async def delete_wechat_material(media_id: str):
    """删除微信素材"""
    # ...
```

## 二、数据采集优化

### 当前问题

1. **GitHub API 限制**：无 token 时 401 错误
2. **RSS 源质量参差不齐**：部分源内容质量低
3. **无去重机制**：可能采集重复内容

### 优化方案

#### 1. 智能源管理

```python
# RSS 源质量评分
class SourceQuality:
    def __init__(self):
        self.scores = {}  # source_url -> score
    
    def update_score(self, source_url: str, article_quality: float):
        """根据文章质量更新源评分"""
        if source_url not in self.scores:
            self.scores[source_url] = []
        
        self.scores[source_url].append(article_quality)
        
        # 保留最近 100 个评分
        if len(self.scores[source_url]) > 100:
            self.scores[source_url] = self.scores[source_url][-100:]
    
    def get_score(self, source_url: str) -> float:
        """获取源评分"""
        scores = self.scores.get(source_url, [])
        return sum(scores) / len(scores) if scores else 0.5
```

#### 2. 内容去重

```python
def deduplicate_articles(articles: list[dict]) -> list[dict]:
    """基于内容相似度去重"""
    from difflib import SequenceMatcher
    
    unique = []
    seen_hashes = set()
    
    for article in articles:
        # 计算内容指纹
        content_hash = hash(article.get("summary", "")[:100])
        
        if content_hash in seen_hashes:
            continue
        
        # 检查与已有文章的相似度
        is_duplicate = False
        for existing in unique:
            similarity = SequenceMatcher(
                None,
                article.get("summary", ""),
                existing.get("summary", "")
            ).ratio()
            
            if similarity > 0.8:  # 80% 相似度视为重复
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique.append(article)
            seen_hashes.add(content_hash)
    
    return unique
```

## 三、内容质量提升

### 优化方案

#### 1. 多轮生成 + 评分选优

```python
def generate_best_content(article: dict, num_versions: int = 3) -> str:
    """生成多个版本，选择最优"""
    versions = []
    
    for i in range(num_versions):
        content = generate_content(article, temperature=0.7 + i * 0.1)
        score = score_content(content)
        versions.append((content, score))
    
    # 选择最高分
    best = max(versions, key=lambda x: x[1])
    return best[0]
```

#### 2. 用户反馈学习

```python
@app.post("/api/feedback")
async def record_feedback(request: Request):
    """记录用户反馈"""
    body = await request.json()
    article_id = body.get("article_id")
    rating = body.get("rating")  # 1-5 分
    comment = body.get("comment")
    
    feedback_file = PROJECT_ROOT / "knowledge" / "feedback.jsonl"
    record = {
        "article_id": article_id,
        "rating": rating,
        "comment": comment,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(feedback_file, "a") as f:
        f.write(json.dumps(record) + "\n")
    
    return {"success": True}
```

## 四、用户体验优化

### 优化方案

#### 1. 实时进度显示

```javascript
// WebSocket 实时进度
const ws = new WebSocket(`ws://${window.location.host}/ws/pipeline`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateProgressBar(data.progress);
    updateStatusText(data.message);
};
```

#### 2. 批量操作

```javascript
// 批量选择文章
function selectAll() {
    document.querySelectorAll('.article-checkbox').forEach(cb => {
        cb.checked = true;
    });
}

// 批量发布
async function batchPublish() {
    const selected = getSelectedArticles();
    for (const article of selected) {
        await publishArticle(article.id);
    }
}
```

## 五、实施优先级

| 优先级 | 功能 | 预估工作量 |
|--------|------|-----------|
| P0 | 草稿箱功能 | 2 小时 |
| P0 | 发布历史 | 1 小时 |
| P1 | 定时发布 | 3 小时 |
| P1 | 内容去重 | 2 小时 |
| P2 | 多轮生成 | 4 小时 |
| P2 | 用户反馈 | 2 小时 |
| P3 | WebSocket 进度 | 4 小时 |
| P3 | 批量操作 | 2 小时 |
