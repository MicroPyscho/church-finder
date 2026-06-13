export function useSEO({ title, description, image, url, type = "website" }: {
  title: string; description: string; image?: string; url?: string; type?: string;
}) {
  const full = title === "Nave"
    ? "Nave — UK Church & Chapel Property Search"
    : `${title} | Nave`;
  document.title = full;
  const set = (name: string, val: string, prop = false) => {
    const attr = prop ? "property" : "name";
    let el = document.querySelector(`meta[${attr}="${name}"]`);
    if (!el) { el = document.createElement("meta"); el.setAttribute(attr, name); document.head.appendChild(el); }
    el.setAttribute("content", val);
  };
  set("description", description);
  set("og:title", full, true); set("og:description", description, true);
  set("og:type", type, true); set("og:site_name", "Nave", true);
  set("twitter:card", "summary"); set("twitter:title", full);
  set("twitter:description", description);
  if (url)   { set("og:url", url, true); }
  if (image) { set("og:image", image, true); set("twitter:image", image); }
}
