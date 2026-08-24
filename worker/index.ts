/**
 * Krypto Directory worker — health check plus SPA assets.
 */

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

export default {
  async fetch(request, _env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/api/health") {
      return json({ ok: true, service: "krypto-directory" });
    }
    return json({ error: "Not found" }, 404);
  },
} satisfies ExportedHandler<Env>;
