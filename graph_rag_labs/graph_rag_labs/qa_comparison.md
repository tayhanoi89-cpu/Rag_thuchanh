# QA Comparison Report (Multi-hop Graph RAG)

- Generated at: 2026-08-12 19:18:20
- Top-k: 5
- Relation filters: CAN_CU, THAY_THE, HOP_NHAT
- Hop settings compared: 0, 1, 2

## Q1

**Question**: Nghi dinh 46/2023/ND-CP thay the cho nghi dinh nao, va nghi dinh bi thay the do co noi dung gi noi bat ve kinh doanh bao hiem?

| Hops | Direct chunks | Hop documents | Hop chunks | Quick assessment | Answer summary |
|---|---:|---:|---:|---|---|
| 0 | 5 | 0 | 0 | Thieu bang chung trong ngu canh | Khong tim thay thong tin trong ngu canh duoc cung cap. |
| 1 | 5 | 2 | 4 | Thieu bang chung trong ngu canh | Khong tim thay thong tin trong ngu canh duoc cung cap. |
| 2 | 5 | 2 | 4 | Thieu bang chung trong ngu canh | Khong tim thay thong tin trong ngu canh duoc cung cap. |

### Full answers

#### Hops = 0

Khong tim thay thong tin trong ngu canh duoc cung cap.

#### Hops = 1

Khong tim thay thong tin trong ngu canh duoc cung cap.

#### Hops = 2

Khong tim thay thong tin trong ngu canh duoc cung cap.

## Q2

**Question**: Van ban hop nhat so 52/VBHN-NHNN duoc hop nhat tu van ban nao, va quy dinh ve ho so, thu tuc cap giay phep lan dau cua ngan hang thuong mai gom nhung tai lieu gi?

| Hops | Direct chunks | Hop documents | Hop chunks | Quick assessment | Answer summary |
|---|---:|---:|---:|---|---|
| 0 | 5 | 0 | 0 | Thieu bang chung trong ngu canh | Khong tim thay thong tin trong ngu canh duoc cung cap. |
| 1 | 5 | 3 | 6 | Thieu bang chung trong ngu canh | Khong tim thay thong tin trong ngu canh duoc cung cap. |
| 2 | 5 | 3 | 6 | Thieu bang chung trong ngu canh | Khong tim thay thong tin trong ngu canh duoc cung cap. |

### Full answers

#### Hops = 0

Khong tim thay thong tin trong ngu canh duoc cung cap.

#### Hops = 1

Khong tim thay thong tin trong ngu canh duoc cung cap.

#### Hops = 2

Khong tim thay thong tin trong ngu canh duoc cung cap.

## Q3

**Question**: Thong tu so 01/2025/TT-NHNN quy dinh ve cap giay phep quy tin dung nhan dan duoc sua doi, bo sung boi van ban nao, va nhung noi dung sua doi bo sung chinh la gi?

| Hops | Direct chunks | Hop documents | Hop chunks | Quick assessment | Answer summary |
|---|---:|---:|---:|---|---|
| 0 | 5 | 0 | 0 | Thieu bang chung trong ngu canh | Khong tim thay thong tin trong ngu canh duoc cung cap. |
| 1 | 0 | 0 | 0 | Chi dua vao ngu canh truc tiep | [ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/ge... |
| 2 | 0 | 0 | 0 | Chi dua vao ngu canh truc tiep | [ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/ge... |

### Full answers

#### Hops = 0

Khong tim thay thong tin trong ngu canh duoc cung cap.

#### Hops = 1

[ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash
Please retry in 619.861723ms. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 20
}
, retry_delay {
}
]

#### Hops = 2

[ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash
Please retry in 59.483167934s. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 20
}
, retry_delay {
  seconds: 59
}
]

## Q4

**Question**: Thong tu so 41/2016/TT-NHNN ve ty le an toan von cua ngan hang can cu vao luat nao, va luat do quy dinh chuc nang nhiem vu cua co quan nao?

| Hops | Direct chunks | Hop documents | Hop chunks | Quick assessment | Answer summary |
|---|---:|---:|---:|---|---|
| 0 | 0 | 0 | 0 | Chi dua vao ngu canh truc tiep | [ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/ge... |
| 1 | 0 | 0 | 0 | Chi dua vao ngu canh truc tiep | [ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/ge... |
| 2 | 0 | 0 | 0 | Chi dua vao ngu canh truc tiep | [ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/ge... |

### Full answers

#### Hops = 0

[ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash
Please retry in 58.090157556s. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 20
}
, retry_delay {
  seconds: 58
}
]

#### Hops = 1

[ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash
Please retry in 56.342380892s. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 20
}
, retry_delay {
  seconds: 56
}
]

#### Hops = 2

[ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 5, model: gemini-3.6-flash
Please retry in 54.893930181s. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 5
}
, retry_delay {
  seconds: 54
}
]

## Q5

**Question**: Hoat dong giao nhan, van chuyen tien mat va tai san quy cua Ngan hang Nha nuoc duoc dieu chinh boi Thong tu nao, va Thong tu do co duoc sua doi bo sung boi van ban nao khong?

| Hops | Direct chunks | Hop documents | Hop chunks | Quick assessment | Answer summary |
|---|---:|---:|---:|---|---|
| 0 | 0 | 0 | 0 | Chi dua vao ngu canh truc tiep | [ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/ge... |
| 1 | 0 | 0 | 0 | Chi dua vao ngu canh truc tiep | [ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/ge... |
| 2 | 0 | 0 | 0 | Chi dua vao ngu canh truc tiep | [ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/ge... |

### Full answers

#### Hops = 0

[ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash
Please retry in 53.698939824s. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 20
}
, retry_delay {
  seconds: 53
}
]

#### Hops = 1

[ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash
Please retry in 52.613760751s. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 20
}
, retry_delay {
  seconds: 52
}
]

#### Hops = 2

[ERROR] ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 5, model: gemini-3.6-flash
Please retry in 51.476010533s. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 5
}
, retry_delay {
  seconds: 51
}
]

## Overall Notes

- Compare whether hops=1/2 improves evidence breadth versus hops=0.
- Check if answers become more complete for cross-document legal relation questions.
- Keep answers grounded: prefer responses with explicit document/chunk evidence.
