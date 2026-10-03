// Builds GoingOnce.pptx (5 slides) in the project root.
//   cd deck && node build_deck.js

const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("./apply_theme.js");

const OUT = path.join(__dirname, "..", "GoingOnce.pptx");

const THEME = {
  name: "GoingOnce",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0F1C2E",     // auction-night navy (dominant)
    lt1: "FFFFFF",
    dk2: "5B6B7F",     // muted slate for captions
    lt2: "F3F5F8",     // card tint
    accent1: "FF6B35", // "SOLD" orange
    accent2: "FFC145", // gavel amber
    accent3: "1FA187", // good / safe teal
    accent4: "3D7BF7",
    accent5: "7C5CFA",
    accent6: "1E2E45", // raised navy surface
    hlink: "3D7BF7",
    folHlink: "7C5CFA",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "GoingOnce";
pres.author = "Team GoingOnce";
const C = pres.SchemeColor;
const S = pres.ShapeType;

const W = 13.333;
const M = 0.6; // side margin

async function icon(Comp, color) {
  let svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { size: 256 }));
  svg = svg.replace(/currentColor/g, "#" + color);
  if (!svg.includes("fill=")) svg = svg.replace("<svg", `<svg fill="#${color}"`);
  const png = await sharp(Buffer.from(svg)).resize(256, 256, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

const shadow = () => ({ type: "outer", color: "0F1C2E", opacity: 0.12, blur: 8, offset: 2, angle: 90 });

// Icon centered in a filled circle: the deck's one repeated motif.
function iconCircle(slide, data, x, y, d, fill, name) {
  slide.addShape(S.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill, width: 0 }, objectName: `${name} circle` });
  const pad = d * 0.25;
  slide.addImage({ data, x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: `${name} icon` });
}

// --- Layouts -------------------------------------------------------------------

const TITLE_BOX = { x: M, y: 0.42, w: W - 2 * M, h: 0.9 };

pres.defineSlideMaster({
  title: "GO Title",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M + 0.2, y: 2.0, w: 7.2, h: 1.3, fontSize: 66, bold: true, color: C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M + 0.2, y: 3.45, w: 7.2, h: 1.3, fontSize: 22, color: C.background1, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});

const footer = (color) => ({ text: { text: "GoingOnce  ·  UB AI for Good Hackathon 2026", options: { x: M, y: 7.02, w: 6, h: 0.3, fontSize: 10, color, margin: 0, isTextBox: true } } });

pres.defineSlideMaster({
  title: "GO Content Light",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", ...TITLE_BOX, fontSize: 36, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    footer(C.text2),
  ],
  slideNumber: { x: W - M - 0.5, y: 7.02, w: 0.5, h: 0.3, fontSize: 10, color: C.text2, align: "right" },
});

pres.defineSlideMaster({
  title: "GO Content Dark",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", ...TITLE_BOX, fontSize: 36, bold: true, color: C.background1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    footer(C.background2),
  ],
  slideNumber: { x: W - M - 0.5, y: 7.02, w: 0.5, h: 0.3, fontSize: 10, color: C.background2, align: "right" },
});

async function main() {
  const I = {
    gavel: await icon(fa.FaGavel, HEX.dk1),
    buyW: await icon(fa.FaShoppingCart, HEX.lt1),
    sellW: await icon(fa.FaCamera, HEX.lt1),
    dealW: await icon(fa.FaHandshake, HEX.lt1),
    fleetW: await icon(fa.FaTruck, HEX.lt1),
    buyN: await icon(fa.FaShoppingCart, HEX.dk1),
    sellN: await icon(fa.FaCamera, HEX.dk1),
    dealN: await icon(fa.FaHandshake, HEX.dk1),
    fleetN: await icon(fa.FaTruck, HEX.dk1),
    shield: await icon(fa.FaShieldAlt, HEX.lt1),
    scale: await icon(fa.FaBalanceScale, HEX.lt1),
    leaf: await icon(fa.FaLeaf, HEX.lt1),
    person: await icon(fa.FaUserCheck, HEX.lt1),
  };

  // --- 1. Title ------------------------------------------------------------------
  pres.addSection({ title: "Opening" });
  const s1 = pres.addSlide({ masterName: "GO Title", sectionTitle: "Opening" });
  s1.addText("TEAM GOINGONCE", { x: M + 0.2, y: 1.55, w: 6, h: 0.4, fontSize: 14, bold: true, color: C.accent2, charSpacing: 4, margin: 0, isTextBox: true, objectName: "Team name" });
  s1.addText("GoingOnce", { placeholder: "title" });
  s1.addText([
    { text: "Going once, going twice… ", options: { color: C.background1 } },
    { text: "SOLD.", options: { color: C.accent1, bold: true, breakLine: true } },
    { text: "Every car finds its best buyer, across ACV and Copart.", options: { color: C.background2, fontSize: 18 } },
  ], { placeholder: "body" });
  s1.addText("UB AI for Good Hackathon  ·  ACV Auctions + Copart Challenge  ·  October 3, 2026", { x: M + 0.2, y: 6.45, w: 7.6, h: 0.4, fontSize: 14, color: C.background2, margin: 0, isTextBox: true, objectName: "Event line" });

  // Gavel "stamp" + the four agents
  s1.addShape(S.ellipse, { x: 8.75, y: 0.95, w: 3.7, h: 3.7, fill: { color: C.text1 }, line: { color: C.accent2, width: 3 }, objectName: "Stamp ring" });
  iconCircle(s1, I.gavel, 9.15, 1.35, 2.9, C.accent1, "Gavel");
  const agents = [["Buy", I.buyW], ["Sell", I.sellW], ["Negotiate", I.dealW], ["Fleet", I.fleetW]];
  agents.forEach(([label, data], i) => {
    const x = 8.35 + i * 1.15;
    iconCircle(s1, data, x + 0.2, 5.15, 0.68, C.accent6, `Agent ${label}`);
    s1.addText(label, { x: x - 0.1, y: 5.9, w: 1.28, h: 0.35, fontSize: 13, color: C.background1, align: "center", margin: 0, isTextBox: true, objectName: `Agent ${label} label` });
  });
  s1.addNotes(
    "0:00–0:15\n" +
    "Hi, we're Team GoingOnce. At every car auction you hear 'going once, going twice'... but a lot of cars never hear 'sold'. " +
    "And ACV only earns when a car sells. We built four AI agents for the combined ACV and Copart that get more cars to 'sold'."
  );

  // --- 2. Problem + solution in STAR ------------------------------------------------
  pres.addSection({ title: "Problem and solution" });
  const s2 = pres.addSlide({ masterName: "GO Content Light", sectionTitle: "Problem and solution" });
  s2.addText("Why cars go unsold, and how we fix it", { placeholder: "title" });

  const cardY = 1.85, cardH = 4.95, gap = 0.3;
  const cardW = (W - 2 * M - 3 * gap) / 4;
  const colX = (i) => M + i * (cardW + gap);
  s2.addText("THE PROBLEM", { x: colX(0), y: 1.42, w: cardW * 2 + gap, h: 0.32, fontSize: 12, bold: true, color: C.text2, charSpacing: 3, margin: 0, isTextBox: true, objectName: "Problem label" });
  s2.addText("OUR SOLUTION", { x: colX(2), y: 1.42, w: cardW * 2 + gap, h: 0.32, fontSize: 12, bold: true, color: C.accent1, charSpacing: 3, margin: 0, isTextBox: true, objectName: "Solution label" });

  const star = [
    { letter: "S", label: "Situation", fill: C.text1 },
    { letter: "T", label: "Task", fill: C.text1 },
    { letter: "A", label: "Action", fill: C.accent1 },
    { letter: "R", label: "Result", fill: C.accent1 },
  ];
  star.forEach((c, i) => {
    const x = colX(i);
    s2.addShape(S.roundRect, { x, y: cardY, w: cardW, h: cardH, rectRadius: 0.12, fill: { color: C.background2 }, line: { color: C.background2, width: 0 }, shadow: shadow(), objectName: `${c.label} card` });
    s2.addShape(S.ellipse, { x: x + 0.25, y: cardY + 0.25, w: 0.62, h: 0.62, fill: { color: c.fill }, line: { color: c.fill, width: 0 }, objectName: `${c.label} letter circle` });
    s2.addText(c.letter, { x: x + 0.25, y: cardY + 0.25, w: 0.62, h: 0.62, fontSize: 22, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `${c.label} letter` });
    s2.addText(c.label, { x: x + 1.0, y: cardY + 0.25, w: cardW - 1.1, h: 0.62, fontSize: 20, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: `${c.label} heading` });
  });

  const bodyX = (i) => colX(i) + 0.25;
  const bodyW = cardW - 0.5;
  const bodyY = cardY + 1.1;
  const bullets = (items) => items.map((t, k) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: k < items.length - 1 } }));

  s2.addText(bullets([
    "ACV runs 20-minute dealer auctions. Copart sells damaged cars worldwide. They are becoming one company.",
    "Cars still go unsold: the right buyer misses the auction, prices don't meet, hidden damage scares buyers.",
    "ACV only earns when a car sells.",
  ]), { x: bodyX(0), y: bodyY, w: bodyW, h: cardH - 1.3, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true, objectName: "Situation text" });

  s2.addText(bullets([
    "Turn more listings into sales across both companies.",
    "Catch hidden damage before anyone buys.",
    "Move cars at the lowest cost, so the combined company earns at every stage of a car's life.",
  ]), { x: bodyX(1), y: bodyY, w: bodyW, h: cardH - 1.3, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true, objectName: "Task text" });

  s2.addText("4 AI agents do the work. People approve.", { x: bodyX(2), y: bodyY, w: bodyW, h: 0.55, fontSize: 14, italic: true, color: C.text2, valign: "top", margin: 0, isTextBox: true, objectName: "Action intro" });
  const actions = [
    ["Buy", "finds cars, checks history", I.buyN],
    ["Sell", "photo report, waiting buyers", I.sellN],
    ["Negotiate", "closes the gap, pays, ships", I.dealN],
    ["Fleet", "full trucks, prices hold", I.fleetN],
  ];
  actions.forEach(([name, desc, data], k) => {
    const y = bodyY + 0.68 + k * 0.84;
    s2.addImage({ data, x: bodyX(2), y: y + 0.04, w: 0.3, h: 0.3, objectName: `Action ${name} icon` });
    s2.addText([{ text: name + ": ", options: { bold: true } }, { text: desc }], { x: bodyX(2) + 0.42, y, w: bodyW - 0.42, h: 0.62, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: `Action ${name} text` });
  });

  s2.addText("In our demo:", { x: bodyX(3), y: bodyY, w: bodyW, h: 0.32, fontSize: 14, italic: true, color: C.text2, margin: 0, isTextBox: true, objectName: "Result intro" });
  const results = [
    ["1", "flood car caught before purchase"],
    ["3", "buyers waiting before the auction"],
    ["$13,150", "deal closed from a $3,000 gap"],
    ["+$349K", "for one 120-car fleet"],
  ];
  results.forEach(([num, cap], k) => {
    const y = bodyY + 0.45 + k * 0.84;
    s2.addText(num, { x: bodyX(3), y, w: bodyW, h: 0.42, fontSize: 24, bold: true, color: C.accent1, fontFace: "+mj-lt", margin: 0, isTextBox: true, objectName: `Result ${k + 1} number` });
    s2.addText(cap, { x: bodyX(3), y: y + 0.42, w: bodyW, h: 0.3, fontSize: 12, color: C.text1, margin: 0, isTextBox: true, objectName: `Result ${k + 1} caption` });
  });
  s2.addNotes(
    "0:15–1:15\n" +
    "Situation: ACV runs 20-minute online auctions for dealers, Copart sells damaged cars to buyers worldwide, and they're becoming one company. " +
    "But cars still go unsold: the right buyer isn't watching, the price doesn't meet, or hidden damage scares buyers off. And ACV only earns on a sale.\n" +
    "Task: turn more listings into sales, catch hidden damage before anyone buys, and move cars at the lowest cost.\n" +
    "Action: GoingOnce is four AI agents that do the work while people approve every money step: Buy, Sell, Negotiate, Fleet.\n" +
    "Result, in our demo: a flood car caught before purchase, three buyers lined up before the auction, a $3,000 price gap closed, and $349K more for one fleet. Let's see it."
  );

  // --- 3. Demo video (area left blank for the recording) ------------------------------
  pres.addSection({ title: "Demo" });
  const s3 = pres.addSlide({ masterName: "GO Content Dark", sectionTitle: "Demo" });
  s3.addText("GoingOnce in action", { placeholder: "title" });
  const vidW = 8.9, vidH = vidW * 9 / 16;
  s3.addShape(S.roundRect, { x: M, y: 1.5, w: vidW, h: vidH, rectRadius: 0.1, fill: { color: C.accent6 }, line: { color: C.accent6, width: 0 }, objectName: "Video area" });
  const steps = [
    ["Buy", "Finds cars, catches hidden damage, asks before bidding", I.buyW],
    ["Sell", "Photo report, best way to sell, buyers already waiting", I.sellW],
    ["Negotiate", "Closes the price gap, then pays, insures and ships", I.dealW],
    ["Fleet", "Moves 120 cars in full trucks so prices hold", I.fleetW],
  ];
  const sx = M + vidW + 0.4;
  steps.forEach(([name, desc, data], k) => {
    const y = 1.55 + k * 1.24;
    iconCircle(s3, data, sx, y, 0.62, C.accent1, `Demo ${name}`);
    s3.addText(name, { x: sx + 0.8, y: y - 0.02, w: W - M - sx - 0.8, h: 0.34, fontSize: 16, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: `Demo ${name} name` });
    s3.addText(desc, { x: sx + 0.8, y: y + 0.32, w: W - M - sx - 0.8, h: 0.78, fontSize: 14, color: C.background2, valign: "top", margin: 0, isTextBox: true, objectName: `Demo ${name} text` });
  });
  s3.addNotes(
    "1:15–3:45 (demo video, about 2.5 minutes)\n" +
    "Buy: 'Reason one: buyers can't find the right car, or can't trust it. It searched ACV and Copart and checked every car's history. This cheap one was flooded and hidden behind a clean title. Nothing is bought without his OK.'\n" +
    "Sell: 'Reason two: the right buyer isn't watching during the auction. AI wrote the condition report, ACV pays her the most, and three buyers are already waiting, including the dealer we just saw.'\n" +
    "Negotiate: 'Reason three: the seller wants $15,000, the top bid is $12,000. The AI shows real market prices, they meet in three rounds, and it closes itself: payment, insurance, loan payoff, title, truck.'\n" +
    "Fleet: 'Reason four is scale. 120 rental cars in full trucks to seven cities: $349K more, $108 a car to ship.'\n" +
    "To add the video: Insert > Video > Video from File, then drag it over the dark area on the left."
  );

  // --- 4. AI for Good ----------------------------------------------------------------
  pres.addSection({ title: "AI for Good" });
  const s4 = pres.addSlide({ masterName: "GO Content Light", sectionTitle: "AI for Good" });
  s4.addText("How GoingOnce supports AI for Good", { placeholder: "title" });
  const goods = [
    ["Protects families from fraud", "Catches flood-damaged cars, washed titles and rolled-back odometers before anyone buys them.", I.shield],
    ["Fair deals for both sides", "Each side keeps its own limit. The AI shows real market prices and never pushes anyone past their limit.", I.scale],
    ["Less waste, fewer emissions", "14 full trucks instead of 98 single trips. Unsold cars reach buyers worldwide instead of the scrapyard.", I.leaf],
    ["People stay in control", "Every step is shown. The AI never spends, lists or signs anything without a person's OK.", I.person],
  ];
  const gW = (W - 2 * M - 0.4) / 2, gH = 2.15;
  goods.forEach(([head, desc, data], k) => {
    const x = M + (k % 2) * (gW + 0.4);
    const y = 1.75 + Math.floor(k / 2) * (gH + 0.4);
    s4.addShape(S.roundRect, { x, y, w: gW, h: gH, rectRadius: 0.12, fill: { color: C.background2 }, line: { color: C.background2, width: 0 }, shadow: shadow(), objectName: `${head} card` });
    iconCircle(s4, data, x + 0.35, y + 0.4, 0.85, C.accent3, head);
    s4.addText(head, { x: x + 1.5, y: y + 0.38, w: gW - 1.8, h: 0.5, fontSize: 20, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: `${head} heading` });
    s4.addText(desc, { x: x + 1.5, y: y + 0.95, w: gW - 1.8, h: 1.2, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: `${head} text` });
  });
  s4.addNotes(
    "3:45–4:25\n" +
    "Why this is AI for Good: it protects families from flood cars, washed titles and odometer fraud before anyone buys. " +
    "Deals are fair: each side keeps its own limit and sees real market prices. " +
    "It cuts waste: full trucks instead of single trips, and unsold cars reach buyers worldwide instead of the scrapyard. " +
    "And people stay in control: the AI never spends money or signs anything without a person's OK."
  );

  // --- 5. Impact + what's next --------------------------------------------------------
  pres.addSection({ title: "Impact and next steps" });
  const s5 = pres.addSlide({ masterName: "GO Content Dark", sectionTitle: "Impact and next steps" });
  s5.addText("Why it matters for ACV, and what's next", { placeholder: "title" });
  const stats = [
    ["$876", "ACV earns on a deal that would have died"],
    ["+$349K", "more for one 120-car fleet"],
    ["66%", "lower transport cost per car"],
  ];
  stats.forEach(([num, cap], k) => {
    const y = 1.6 + k * 1.3;
    s5.addText(num, { x: M, y, w: 5.4, h: 0.8, fontSize: 48, bold: true, color: C.accent2, fontFace: "+mj-lt", margin: 0, isTextBox: true, objectName: `Stat ${k + 1} number` });
    s5.addText(cap, { x: M, y: y + 0.78, w: 5.4, h: 0.36, fontSize: 15, color: C.background1, margin: 0, isTextBox: true, objectName: `Stat ${k + 1} caption` });
  });
  s5.addText("Numbers from our demo data", { x: M, y: 5.45, w: 5.4, h: 0.3, fontSize: 11, italic: true, color: C.background2, margin: 0, isTextBox: true, objectName: "Stats note" });

  const rx = 6.9;
  const road = [
    ["Today", "4 working AI agents on demo data"],
    ["Next", "Connect to ACV + Copart inventory, inspections, financing and transport"],
    ["Then", "Car Health Score for lenders and insurers, more overseas buyers, consumer sellers"],
  ];
  s5.addShape(S.line, { x: rx + 0.3, y: 2.0, w: 0, h: 2.6, line: { color: C.accent6, width: 3 }, objectName: "Roadmap connector" });
  road.forEach(([when, what], k) => {
    const y = 1.7 + k * 1.3;
    s5.addShape(S.ellipse, { x: rx, y, w: 0.6, h: 0.6, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: `Roadmap ${when} circle` });
    s5.addText(String(k + 1), { x: rx, y, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `Roadmap ${when} number` });
    s5.addText(when, { x: rx + 0.85, y: y - 0.02, w: W - M - rx - 0.85, h: 0.36, fontSize: 18, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: `Roadmap ${when} heading` });
    s5.addText(what, { x: rx + 0.85, y: y + 0.36, w: W - M - rx - 0.85, h: 0.75, fontSize: 14, color: C.background2, valign: "top", margin: 0, isTextBox: true, objectName: `Roadmap ${when} text` });
  });

  s5.addText([
    { text: "Going once, going twice… ", options: { color: C.background1 } },
    { text: "SOLD.", options: { color: C.accent1, bold: true } },
  ], { x: M, y: 5.95, w: W - 2 * M, h: 0.62, fontSize: 30, italic: true, fontFace: "+mj-lt", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "Closing line" });
  s5.addText("Shaped by feedback from ACV mentors at the hackathon", { x: M, y: 6.55, w: W - 2 * M, h: 0.32, fontSize: 12, color: C.background2, align: "center", margin: 0, isTextBox: true, objectName: "Mentor note" });
  s5.addNotes(
    "4:25–5:00\n" +
    "For ACV: every rescued deal is revenue that would have been zero, like the $876 in our demo, and fleets earn far more with lower transport. " +
    "Today it's four working agents on demo data. Next, connect them to ACV and Copart's real inventory, inspections, financing and transport. " +
    "Then, a Car Health Score that lenders and insurers can use, and more buyers worldwide. " +
    "We shaped this with feedback from ACV's mentors. Going once, going twice... sold. Thank you."
  );

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });
