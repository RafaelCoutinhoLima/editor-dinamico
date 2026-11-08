import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Same free fonts edin uses for its ASS captions (SIL OFL, assets/fonts). The bridge copies them
// to public/edin/fonts before every render.
export const DISPLAY = "Anton";
export const BODY = "Montserrat";

loadFont({ family: DISPLAY, url: staticFile("edin/fonts/Anton-Regular.ttf"), weight: "400" });
loadFont({ family: BODY, url: staticFile("edin/fonts/Montserrat-ExtraBold.ttf"), weight: "800" });
