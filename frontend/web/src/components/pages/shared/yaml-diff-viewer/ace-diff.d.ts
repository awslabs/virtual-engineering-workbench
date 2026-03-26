declare module 'ace-diff' {
  interface AceDiffEditorOptions {
    content: string,
    editable?: boolean,
    copyLinkEnabled?: boolean,
    mode?: string,
    theme?: string,
  }

  interface AceDiffOptions {
    ace: object,
    element: HTMLElement | null,
    mode?: string,
    theme?: string,
    lockScrolling?: boolean,
    showConnectors?: boolean,
    left: AceDiffEditorOptions,
    right: AceDiffEditorOptions,
  }

  interface AceDiffEditors {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    left: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    right: any,
  }

  class AceDiff {
    lineHeight: number;
    constructor(options: AceDiffOptions);
    destroy(): void;
    diff(): void;
    getEditors(): AceDiffEditors;
  }

  export default AceDiff;
}
