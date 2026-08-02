"""角色扮演场景配置（T-005）。

每个场景包含：id、名称、图标、Agent 角色、描述、难度、标签、
角色性格补充（system_prompt_additions）、开场白（opening）。
"""

ROLEPLAY_SCENARIOS = {
    "restaurant": {
        "id": "restaurant",
        "name": "餐厅点餐",
        "icon": "🍽️",
        "role": "餐厅服务员",
        "description": "在餐厅与服务员交流，练习点餐、询问菜品、支付等场景",
        "difficulty": "easy",
        "tags": ["日常生活", "餐饮"],
        "system_prompt_additions": "你是一位友好、耐心的餐厅服务员，态度热情但不夸张。",
        "opening": "您好！欢迎光临本餐厅！请问您想坐在哪边？我们有靠窗和卡座位置。",
    },
    "travel": {
        "id": "travel",
        "name": "旅行问路",
        "icon": "🗺️",
        "role": "当地路人",
        "description": "在旅行中向当地人问路，练习方向、交通、景点等表达",
        "difficulty": "easy",
        "tags": ["旅行", "交通"],
        "system_prompt_additions": "你是一位热心的当地居民，熟悉这个城市，乐于助人。",
        "opening": "你好！你是游客吗？需要帮忙指路吗？",
    },
    "hotel": {
        "id": "hotel",
        "name": "酒店入住",
        "icon": "🏨",
        "role": "酒店前台",
        "description": "在酒店办理入住，练习预订、登记、咨询等服务场景",
        "difficulty": "medium",
        "tags": ["旅行", "住宿"],
        "system_prompt_additions": "你是一位专业的酒店前台工作人员，服务周到、用语规范。",
        "opening": "下午好！欢迎光临。请问您有预订吗？可以告诉我您的姓名吗？",
    },
    "shopping": {
        "id": "shopping",
        "name": "购物",
        "icon": "🛍️",
        "role": "店员",
        "description": "在商店购物，练习询问价格、尺寸、颜色、退换货等对话",
        "difficulty": "medium",
        "tags": ["购物", "日常生活"],
        "system_prompt_additions": "你是一位热情、专业的店员，善于帮助顾客找到合适的产品。",
        "opening": "欢迎光临！今天想看看什么？我们刚到了新款衣服。",
    },
    "interview": {
        "id": "interview",
        "name": "面试",
        "icon": "💼",
        "role": "面试官",
        "description": "参加英语面试，练习自我介绍、职业规划、回答问题等",
        "difficulty": "hard",
        "tags": ["职业", "职场"],
        "system_prompt_additions": "你是一位专业的面试官，问题有针对性，态度友好但保持专业性。",
        "opening": "请坐。我们先从自我介绍开始吧。请简单介绍一下你的背景。",
    },
}
