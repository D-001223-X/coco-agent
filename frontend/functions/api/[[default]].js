// EdgeOne Pages 反向代理：将 /api/* 请求转发到 Railway 后端
// 原理：国内用户直连 EdgeOne 边缘节点，EdgeOne 服务端转发到 Railway（服务器间通信不受 GFW 影响）
const BACKEND_URL = "https://coco-agent-production.up.railway.app";

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);

  // 仅处理 /api/ 前缀的请求，其余交给静态资源
  if (!url.pathname.startsWith("/api/") && url.pathname !== "/api") {
    return new Response("Not Found", { status: 404 });
  }

  const target = BACKEND_URL + url.pathname + url.search;

  const headers = new Headers(request.headers);
  headers.delete("host");

  const init = {
    method: request.method,
    headers,
    redirect: "follow",
  };

  // GET/HEAD 不携带 body，其余方法透传请求体
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
  }

  // CORS 预检请求直接放行
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders(),
    });
  }

  try {
    const resp = await fetch(target, init);
    const respHeaders = new Headers(resp.headers);
    // 允许跨域（如前端和函数不同源时）
    for (const [key, value] of Object.entries(corsHeaders())) {
      respHeaders.set(key, value);
    }
    return new Response(resp.body, {
      status: resp.status,
      headers: respHeaders,
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ detail: "后端服务暂不可用，请稍后重试" }),
      {
        status: 502,
        headers: { "content-type": "application/json", ...corsHeaders() },
      }
    );
  }
}

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
    "access-control-allow-headers":
      "authorization, content-type, x-requested-with",
  };
}
