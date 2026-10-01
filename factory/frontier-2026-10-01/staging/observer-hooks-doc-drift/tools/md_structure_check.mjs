// Structural check of the post_api_request field list in observer-hooks.md
// (CommonMark + GFM via mdast-util-from-markdown), plus a static MDX-hazard
// scan of the lines the branch adds. Usage:
//   node md_structure_check.mjs <node_modules dir> <base.md> <head.md> <added_lines.txt>
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const [nm, basePath, headPath, addedPath] = process.argv.slice(2);
const imp = (p) => import(pathToFileURL(`${nm}/${p}`).href);
const { fromMarkdown } = await imp("mdast-util-from-markdown/index.js");
const { gfm } = await imp("micromark-extension-gfm/index.js");
const { gfmFromMarkdown } = await imp("mdast-util-gfm/index.js");

function listAfter(md, lead) {
  const tree = fromMarkdown(md, { extensions: [gfm()], mdastExtensions: [gfmFromMarkdown()] });
  const kids = tree.children;
  const i = kids.findIndex(
    (n) => n.type === "paragraph" && n.children[0]?.type === "inlineCode" && n.children[0].value === lead,
  );
  const list = kids[i + 1];
  if (i < 0 || list?.type !== "list") return null;
  return list.children.map((li) => {
    const para = li.children[0];
    const codes = para.children.filter((c) => c.type === "inlineCode").map((c) => c.value);
    return { first_code: codes[0], inline_code_count: codes.length, paragraphs: li.children.length };
  });
}

const base = listAfter(readFileSync(basePath, "utf8"), "post_api_request");
const head = listAfter(readFileSync(headPath, "utf8"), "post_api_request");
const added = readFileSync(addedPath, "utf8").split("\n").filter(Boolean);
const hazards = [];
for (const line of added) {
  const outsideCode = line.replace(/`[^`]*`/g, "");
  if (/[{}<>]/.test(outsideCode)) hazards.push({ line, why: "MDX-significant character outside code span" });
  if (/[^\x00-\x7f]/.test(line)) hazards.push({ line, why: "non-ASCII" });
  if (/[─-╿]|\+-{2,}|-{2,}\+/.test(line)) hazards.push({ line, why: "diagram/box-drawing pattern" });
}
const headFirst = (head || []).map((x) => x.first_code);
const result = {
  base_items: base?.length ?? null,
  head_items: head?.length ?? null,
  head_first_codes: headFirst,
  new_items_are_single_paragraph: (head || [])
    .filter((x) => ["first_chunk_at", "context_length", "moa_references"].includes(x.first_code))
    .every((x) => x.paragraphs === 1),
  added_lines: added.length,
  mdx_hazards: hazards,
};
result.pass =
  result.base_items === 6 &&
  result.head_items === 9 &&
  ["first_chunk_at", "context_length", "moa_references"].every((f) => headFirst.includes(f)) &&
  result.new_items_are_single_paragraph &&
  hazards.length === 0;
console.log(JSON.stringify(result, null, 2));
process.exit(result.pass ? 0 : 1);
