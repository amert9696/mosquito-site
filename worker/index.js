// Serves the static site. Keeps one address per page: https, no www, and legal pages stay at their .html paths
// (App Store Connect and the sitemap point at privacy.html / terms.html).
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === "www.mosquitosim.com" || url.protocol === "http:") {
      url.hostname = "mosquitosim.com";
      url.protocol = "https:";
      return Response.redirect(url.toString(), 301);
    }
    if (url.pathname.endsWith(".html") && !url.pathname.endsWith("/index.html")) {
      const bare = new URL(url);
      bare.pathname = url.pathname.slice(0, -5);
      return env.ASSETS.fetch(new Request(bare, request));
    }
    return env.ASSETS.fetch(request);
  },
};
