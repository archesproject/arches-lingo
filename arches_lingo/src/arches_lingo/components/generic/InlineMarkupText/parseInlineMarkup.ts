export interface InlineMarkupSegment {
    text: string;
    style?: "strong" | "emphasis";
    url?: string;
}

/*
 * Recognizes **strong**, *emphasis* and [label](url).  The strong alternative is
 * listed first so that a run of two asterisks is never consumed as emphasis.
 */
const INLINE_MARKUP_PATTERN = /\*\*(.+?)\*\*|\*(.+?)\*|\[(.+?)\]\(([^)]+)\)/g;

/**
 * Splits a string containing a small subset of markdown into renderable
 * segments.  This keeps each translatable message a whole sentence — the markup
 * travels inside the message, so translators are free to reorder the emphasized
 * and linked phrases to suit their own grammar.
 */
export function parseInlineMarkup(markup: string): InlineMarkupSegment[] {
    const segments: InlineMarkupSegment[] = [];
    let plainTextStart = 0;

    for (const match of markup.matchAll(INLINE_MARKUP_PATTERN)) {
        const [matchedMarkup, strongText, emphasisText, linkLabel, linkUrl] =
            match;

        if (match.index > plainTextStart) {
            segments.push({ text: markup.slice(plainTextStart, match.index) });
        }

        if (strongText !== undefined) {
            segments.push({ text: strongText, style: "strong" });
        } else if (emphasisText !== undefined) {
            segments.push({ text: emphasisText, style: "emphasis" });
        } else {
            segments.push({ text: linkLabel, url: linkUrl });
        }

        plainTextStart = match.index + matchedMarkup.length;
    }

    if (plainTextStart < markup.length) {
        segments.push({ text: markup.slice(plainTextStart) });
    }

    return segments;
}
