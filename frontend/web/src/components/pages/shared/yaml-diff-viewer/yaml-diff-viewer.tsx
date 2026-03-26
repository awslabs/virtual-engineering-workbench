import { Badge, Button, Modal, SpaceBetween } from '@cloudscape-design/components';
import { FC, useEffect, useMemo, useRef, useState } from 'react';
import { diffLines, Change } from 'diff';
import { i18n } from './yaml-diff-viewer.translations';
import './yaml-diff-viewer.scss';

interface YamlDiffViewerProps {
  originalYaml: string,
  modifiedYaml: string,
  cfCompatible?: boolean,
}

const ZERO = 0;
const ONE = 1;
const TWO = 2;
const CURSOR_RESET = -1;
const TRAILING_NEWLINE = /\n$/u;

type LineClass = 'removed' | 'added' | 'unchanged' | 'pad';

interface AlignedDiff {
  leftLines: string[],
  rightLines: string[],
  leftClasses: LineClass[],
  rightClasses: LineClass[],
  leftLineNums: (number | null)[],
  rightLineNums: (number | null)[],
}

function splitLines(value: string): string[] {
  return value.replace(TRAILING_NEWLINE, '').split('\n');
}

function pushModificationPair(
  diff: AlignedDiff, removed: string[], added: string[],
  leftNum: { value: number }, rightNum: { value: number },
) {
  const maxLen = Math.max(removed.length, added.length);
  for (let j = ZERO; j < maxLen; j++) {
    const hasLeft = j < removed.length;
    const hasRight = j < added.length;
    diff.leftLines.push(hasLeft ? removed[j] : '');
    diff.leftClasses.push(hasLeft ? 'removed' : 'pad');
    diff.leftLineNums.push(hasLeft ? ++leftNum.value : null);
    diff.rightLines.push(hasRight ? added[j] : '');
    diff.rightClasses.push(hasRight ? 'added' : 'pad');
    diff.rightLineNums.push(hasRight ? ++rightNum.value : null);
  }
}

function pushRemoved(diff: AlignedDiff, lines: string[], leftNum: { value: number }) {
  for (const line of lines) {
    diff.leftLines.push(line);
    diff.leftClasses.push('removed');
    diff.leftLineNums.push(++leftNum.value);
    diff.rightLines.push('');
    diff.rightClasses.push('pad');
    diff.rightLineNums.push(null);
  }
}

function pushAdded(diff: AlignedDiff, lines: string[], rightNum: { value: number }) {
  for (const line of lines) {
    diff.leftLines.push('');
    diff.leftClasses.push('pad');
    diff.leftLineNums.push(null);
    diff.rightLines.push(line);
    diff.rightClasses.push('added');
    diff.rightLineNums.push(++rightNum.value);
  }
}

function pushUnchanged(
  diff: AlignedDiff, lines: string[],
  leftNum: { value: number }, rightNum: { value: number },
) {
  for (const line of lines) {
    diff.leftLines.push(line);
    diff.leftClasses.push('unchanged');
    diff.leftLineNums.push(++leftNum.value);
    diff.rightLines.push(line);
    diff.rightClasses.push('unchanged');
    diff.rightLineNums.push(++rightNum.value);
  }
}

/** Compute aligned left/right content with padding lines so both have equal height */
function alignDiff(original: string, modified: string): AlignedDiff {
  const diff: AlignedDiff = {
    leftLines: [], rightLines: [],
    leftClasses: [], rightClasses: [],
    leftLineNums: [], rightLineNums: [],
  };
  const leftNum = { value: ZERO };
  const rightNum = { value: ZERO };

  const parts: Change[] = diffLines(original, modified);
  let idx = ZERO;
  while (idx < parts.length) {
    const part = parts[idx];

    // Pair consecutive removed+added as a modification
    if (part.removed && idx + ONE < parts.length && parts[idx + ONE].added) {
      pushModificationPair(
        diff, splitLines(part.value), splitLines(parts[idx + ONE].value), leftNum, rightNum,
      );
      idx += TWO;
      continue;
    }

    const lines = splitLines(part.value);
    if (part.removed) {
      pushRemoved(diff, lines, leftNum);
    } else if (part.added) {
      pushAdded(diff, lines, rightNum);
    } else {
      pushUnchanged(diff, lines, leftNum, rightNum);
    }
    idx++;
  }

  return diff;
}

const AlignedDiffView: FC<{
  originalYaml: string,
  modifiedYaml: string,
}> = ({ originalYaml, modifiedYaml }) => {
  const [aceLoaded, setAceLoaded] = useState(false);
  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const leftEditorRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rightEditorRef = useRef<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const aceRef = useRef<any>(null);

  useEffect(() => {
    const loadAce = async () => {
      const ace = await import('ace-builds');
      await import('ace-builds/src-noconflict/mode-yaml');
      await import('ace-builds/src-noconflict/theme-dawn');
      aceRef.current = ace;
      setAceLoaded(true);
    };
    loadAce();
  }, []);

  useEffect(() => {
    if (!leftRef.current || !rightRef.current || !aceLoaded || !aceRef.current) {
      return undefined;
    }

    const ace = aceRef.current;
    const { leftLines, rightLines, leftClasses, rightClasses, leftLineNums, rightLineNums } =
      alignDiff(originalYaml, modifiedYaml);

    // Create editors
    const left = ace.edit(leftRef.current);
    const right = ace.edit(rightRef.current);
    leftEditorRef.current = left;
    rightEditorRef.current = right;

    for (const editor of [left, right]) {
      editor.setTheme('ace/theme/dawn');
      editor.session.setMode('ace/mode/yaml');
      editor.setReadOnly(true);
      editor.setHighlightActiveLine(false);
      editor.setHighlightGutterLine(false);
      editor.setOption('useWorker', false);
      editor.setOption('displayIndentGuides', false);
      editor.setOption('wrap', true);
      editor.setOption('hScrollBarAlwaysVisible', false);
      editor.setOption('highlightSelectedWord', false);
      editor.renderer.$cursorLayer.element.style.display = 'none';
      editor.renderer.setScrollMargin(ZERO, ZERO, ZERO, ZERO);
      editor.renderer.setHScrollBarAlwaysVisible(false);
      editor.setShowFoldWidgets(false);
      editor.renderer.setShowGutter(true);
    }

    left.setValue(leftLines.join('\n'), CURSOR_RESET);
    right.setValue(rightLines.join('\n'), CURSOR_RESET);

    // Custom gutter: show real file line numbers, blank for padding
    const makeGutterRenderer = (lineNums: (number | null)[]) => ({
      getWidth: (
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        session: any, lastLineNumber: number, config: any
      ) => String(lastLineNumber).length * config.characterWidth,
      getText: (_session: unknown, row: number) =>
        lineNums[row] !== null && lineNums[row] !== undefined ? String(lineNums[row]) : '',
    });
    left.session.gutterRenderer = makeGutterRenderer(leftLineNums);
    right.session.gutterRenderer = makeGutterRenderer(rightLineNums);

    // Apply line decorations
    leftClasses.forEach((cls, lineIdx) => {
      if (cls === 'removed') { left.session.addGutterDecoration(lineIdx, 'diff-removed'); }
      if (cls === 'pad') { left.session.addGutterDecoration(lineIdx, 'diff-pad'); }
    });
    rightClasses.forEach((cls, lineIdx) => {
      if (cls === 'added') { right.session.addGutterDecoration(lineIdx, 'diff-added'); }
      if (cls === 'pad') { right.session.addGutterDecoration(lineIdx, 'diff-pad'); }
    });

    // Add line highlights via markers
    const Range = ace.Range || (ace.acequire || ace.require)('ace/range').Range;
    leftClasses.forEach((cls, lineIdx) => {
      if (cls !== 'unchanged') {
        left.session.addMarker(new Range(lineIdx, ZERO, lineIdx, ONE), `diff-line-${cls}`, 'fullLine');
      }
    });
    rightClasses.forEach((cls, lineIdx) => {
      if (cls !== 'unchanged') {
        right.session.addMarker(new Range(lineIdx, ZERO, lineIdx, ONE), `diff-line-${cls}`, 'fullLine');
      }
    });

    // 1:1 scroll sync (both sides are equal height after alignment)
    let isSyncing = false;
    const sync = (
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      source: any, target: any
    ) => {
      if (isSyncing) { return; }
      isSyncing = true;
      target.session.setScrollTop(source.session.getScrollTop());
      isSyncing = false;
    };
    left.session.on('changeScrollTop', () => sync(left, right));
    right.session.on('changeScrollTop', () => sync(right, left));

    return () => {
      left.destroy();
      right.destroy();
      leftEditorRef.current = null;
      rightEditorRef.current = null;
    };
  }, [originalYaml, modifiedYaml, aceLoaded]);

  return (
    <div className="yaml-aligned-diff">
      <div ref={leftRef} className="yaml-aligned-diff__editor" />
      <div ref={rightRef} className="yaml-aligned-diff__editor" />
    </div>
  );
};

export const YamlDiffViewer: FC<YamlDiffViewerProps> = ({
  originalYaml,
  modifiedYaml,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const { additions, deletions } = useMemo(() => {
    const parts = diffLines(originalYaml, modifiedYaml);
    const countLines = (
      value: string
    ) => value.split('\n').filter((l, idx, arr) => idx < arr.length - ONE || l !== '').length;
    return {
      additions: parts.filter(p => p.added).reduce((sum, p) => sum + countLines(p.value), ZERO),
      deletions: parts.filter(p => p.removed).reduce((sum, p) => sum + countLines(p.value), ZERO),
    };
  }, [originalYaml, modifiedYaml]);

  return (
    <>
      <SpaceBetween direction="vertical" size="xs">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <SpaceBetween direction="horizontal" size="xs">
            {additions === ZERO && deletions === ZERO && <Badge color="blue">{i18n.noChanges}</Badge>}
            {additions > ZERO && <Badge color="green">{additions} {i18n.additions}</Badge>}
            {deletions > ZERO && <Badge color="red">{deletions} {i18n.deletions}</Badge>}
          </SpaceBetween>
          <Button iconName="expand" onClick={() => setIsExpanded(true)} ariaLabel={i18n.expandButton}>
            {i18n.expandButton}
          </Button>
        </div>
        <AlignedDiffView originalYaml={originalYaml} modifiedYaml={modifiedYaml} />
      </SpaceBetween>
      <Modal
        visible={isExpanded}
        onDismiss={() => setIsExpanded(false)}
        size="max"
        header={i18n.expandModalHeader}
      >
        <AlignedDiffView originalYaml={originalYaml} modifiedYaml={modifiedYaml} />
      </Modal>
    </>
  );
};
