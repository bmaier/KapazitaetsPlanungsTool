import { Tooltip } from '@mui/material'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'

interface Props {
  text: string
  placement?: 'top' | 'bottom' | 'left' | 'right'
}

export default function HelpTooltip({ text, placement = 'top' }: Props) {
  return (
    <Tooltip title={text} arrow placement={placement} enterTouchDelay={0}>
      <HelpOutlineIcon
        sx={{ fontSize: 14, color: 'text.disabled', verticalAlign: 'middle', ml: 0.5, cursor: 'help' }}
        aria-label={`Hilfe: ${text}`}
      />
    </Tooltip>
  )
}
