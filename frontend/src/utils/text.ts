/**
 * Clean scraped text for display.
 * Removes markdown, HTML entities, JS artifacts, auction jargon.
 */

export function cleanDescription(raw: string | null | undefined): string {
  if (!raw) return "";

  let text = raw
    // Remove markdown headers (##, ###, etc)
    .replace(/^#{1,6}\s+/gm, "")
    // Remove bold/italic markers **text** or *text*
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    // Remove [DISTRESS SIGNAL] and [ANY TAG] style markers
    .replace(/\[[^\]]*\]/g, "")
    // Remove markdown bullet points at line start
    .replace(/^[-*•–]\s+/gm, "")
    // Remove "Source:", "Location:", "Price:" label artifacts
    .replace(/\*?\*?(Source|Location|Price|About this property|Key considerations)\*?\*?:?\s*/gi, "")
    // Remove boilerplate advisory lines
    .replace(/Verify planning permissions for intended use\.?\n?/gi, "")
    .replace(/Commission a structural survey before purchase\.?\n?/gi, "")
    .replace(/Check listed building status with Historic England\.?\n?/gi, "")
    .replace(/Review any restrictive covenants on the title\.?\n?/gi, "")
    .replace(/Confirm utility connections and access rights\.?\n?/gi, "")
    // Remove auction UI junk
    .replace(/Add to (favorites|favourites|bookmarks|compare)\s*/gi, "")
    .replace(/View detail\s*/gi, "")
    .replace(/Add Brochure to List\s*/gi, "")
    .replace(/LOT\s+\d+\s*/gi, "")
    // Remove HTML entities
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&nbsp;/g, " ")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&pound;/g, "£")
    .replace(/&#\d+;/g, "")
    .replace(/&[a-z]+;/gi, "")
    // Remove non-breaking spaces and other invisible unicode
    .replace(/\u00a0/g, " ")
    .replace(/\u200b/g, "")
    .replace(/\u2019/g, "'")
    .replace(/\u2018/g, "'")
    .replace(/\u201c/g, '"')
    .replace(/\u201d/g, '"')
    .replace(/\u2013/g, "-")
    .replace(/\u2014/g, "-")
    // Remove URLs mixed into text
    .replace(/https?:\/\/\S+/g, "")
    // Remove standalone # symbols not part of heading (already stripped above)
    .replace(/\s#\s/g, " ")
    .replace(/^#$/gm, "")
    // Remove lines that are just symbols or very short junk
    .replace(/^[^a-zA-Z0-9£]{1,4}$/gm, "")
    // Collapse multiple newlines to max 2
    .replace(/\n{3,}/g, "\n\n")
    // Collapse multiple spaces
    .replace(/[ \t]{2,}/g, " ")
    // Clean up lines
    .split("\n")
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .join(" ")
    .trim();

  return text;
}

/**
 * Short snippet for card display, cleaned and truncated.
 */
export function descriptionSnippet(
  raw: string | null | undefined,
  maxLen = 130
): string {
  const clean = cleanDescription(raw);
  if (!clean) return "";
  if (clean.length <= maxLen) return clean;
  // Break at word boundary
  return clean.slice(0, maxLen).replace(/\s+\S*$/, "") + "…";
}
