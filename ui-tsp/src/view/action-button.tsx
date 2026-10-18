import type { Children, CommonProps, JSX, KbdProps, StackProps, TextProps } from '@stencil-hq/tern'

interface ActionButtonProps extends CommonProps, Omit<StackProps, 'wrap'>, TextProps, KbdProps {
  children?: Children
  disabled?: boolean
  onClick?: () => void
}

/** A real host button: named, focusable and activated by keyboard, pointer or AX. */
export function ActionButton({ children, disabled, onClick, keys, spans, text, aria, title, ...props }: ActionButtonProps): JSX.Element {
  const label = text ?? spans?.map(span => typeof span === 'string' ? span : span.t).join('')

  return (
    <el aria={aria ?? title} disabled={disabled || !onClick} key={props.key} onClick={onClick} role={props.role}
      tag="button" text={label} title={title} tone={props.tone}>
      {children || keys ? (
        <row align={props.align ?? 'center'} gap={props.gap ?? 'xs'} key="content">
          {children}
          {keys ? <kbd key="keys" keys={keys} /> : null}
        </row>
      ) : null}
    </el>
  )
}
