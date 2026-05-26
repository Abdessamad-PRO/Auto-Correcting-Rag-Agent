import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { inject } from '@angular/core';
import { marked } from 'marked';

/**
 * Renders LLM markdown safely. Uses ``marked`` synchronously; output is marked
 * as trusted HTML because the source is our own backend's structured LLM
 * response — never user-supplied raw HTML.
 *
 * Styling is scoped to the ``.markdown-body`` class set on the root element
 * (rules live in src/styles.css so other components can opt in too).
 */
@Component({
  selector: 'app-markdown',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="markdown-body" [innerHTML]="html()"></div>`,
})
export class MarkdownComponent {
  private readonly sanitizer = inject(DomSanitizer);

  readonly content = input<string | null | undefined>('');

  protected readonly html = computed<SafeHtml>(() => {
    // Defensive: deepseek-r1 occasionally emits <think>...</think> blocks
    // even after backend stripping. Remove them again here so partial /
    // streamed outputs never expose the chain-of-thought scratchpad.
    const src = (this.content() ?? '')
      .replace(/<think>[\s\S]*?<\/think>/gi, '')
      .trim();
    if (!src) return '';
    const raw = marked.parse(src, {
      breaks: true,
      gfm: true,
      async: false,
    }) as string;
    // Backend-controlled content; bypass to allow our own HTML.
    return this.sanitizer.bypassSecurityTrustHtml(raw);
  });
}
