export function cleanDescription(raw: string | null | undefined): string {
  if (!raw) return "";
  return raw
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]/g, "")
    .replace(/^[-*•]\s+/gm, "")
    .replace(/\*?\*?(Source|Location|Price|About this property|Key considerations)\*?\*?:?\s*/gi, "")
    .replace(/Verify planning permissions for intended use\.?\n?/gi, "")
    .replace(/Commission a structural survey before purchase\.?\n?/gi, "")
    .replace(/Check listed building status with Historic England\.?\n?/gi, "")
    .replace(/Review any restrictive covenants on the title\.?\n?/gi, "")
    .replace(/Confirm utility connections and access rights\.?\n?/gi, "")
    .replace(/Add to (favorites|bookmarks|compare)\s*/gi, "")
    .replace(/View detail\s*/gi, "")
    .replace(/Add Brochure to List\s*/gi, "")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/  +/g, " ")
    .trim();
}

export function descriptionSnippet(raw: string | null | undefined, maxLen = 130): string {
  const clean = cleanDescription(raw);
  if (!clean) return "";
  if (clean.length <= maxLen) return clean;
  return clean.slice(0, maxLen).replace(/\s+\S*$/, "") + "…";
}
