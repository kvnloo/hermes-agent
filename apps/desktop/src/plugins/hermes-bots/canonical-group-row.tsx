import {
  cn,
  Codicon,
  ConfirmDialog,
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger,
  GlyphSpinner,
  haptic,
  RowButton,
  useI18n,
  useValue
} from '@hermes/plugin-sdk'
import { useState } from 'react'

import { $canonicalRoomLive, canonicalRoomLiveKey } from './canonical-group-details'
import { useCanonicalGroupLabels } from './canonical-group-labels'
import { disbandGatewayGroupRoom, type GatewayGroupRoom } from './canonical-group-registry'
import { $groupChats } from './group-chat'
import { RoomBotAvatar } from './group-room-avatar'
import { AvatarStack } from './group-room-ui'
import { useBots } from './i18n'
import { rowAge } from './row-age'
import {
  $botSections,
  $draggingBot,
  BOT_DRAG_MIME,
  GATEWAY_GROUP_DRAG_PREFIX,
  gatewayGroupSectionId,
  moveGatewayGroupToSection
} from './user-sections'

interface CanonicalGroupRowProps {
  active: boolean
  onNewSection: (room: GatewayGroupRoom) => void
  onOpen: () => void
  room: GatewayGroupRoom
}

/** One gateway Group Chat in the Bots roster. Same shape as a Desktop group
 *  row (tile, name, age, member line) so the two kinds read as one list; the
 *  live state is whatever an open view of the room last published. */
export function CanonicalGroupRow({ active, onNewSection, onOpen, room }: CanonicalGroupRowProps) {
  const { t } = useI18n()
  const labels = useCanonicalGroupLabels()
  const b = useBots()
  const { group } = b
  const sections = useValue($botSections)
  const currentSectionId = gatewayGroupSectionId(room, useValue($groupChats))
  const dragKey = `${GATEWAY_GROUP_DRAG_PREFIX}${room.key}`
  const dragging = useValue($draggingBot) === dragKey
  const [confirming, setConfirming] = useState(false)
  const live = useValue($canonicalRoomLive)[canonicalRoomLiveKey(room.binding, room.binding.roomId)]
  const state = live?.needsYou ? 'needsYou' : live?.failed ? 'failed' : live?.working ? 'working' : null
  const memberCount = group.memberCount(room.members.length)

  const open = () => {
    haptic('tap')
    onOpen()
  }

  return (
    <>
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <RowButton
            aria-label={room.name}
            className={cn(
              'flex w-full min-w-0 max-w-full items-center gap-2.5 overflow-hidden rounded-md px-2 py-2 text-left transition-colors',
              'hover:bg-(--chrome-action-hover)',
              active && 'bg-(--ui-row-active-background)',
              dragging && 'opacity-40'
            )}
            draggable
            onClick={open}
            onDragEnd={() => $draggingBot.set(null)}
            onDragStart={event => {
              event.dataTransfer.setData(BOT_DRAG_MIME, dragKey)
              event.dataTransfer.effectAllowed = 'move'
              $draggingBot.set(dragKey)
            }}
          >
            <span className="flex w-[34px] shrink-0 items-center justify-center">
              <span className="flex size-8 items-center justify-center rounded-md bg-(--chrome-action-hover) text-(--ui-text-tertiary)">
                <Codicon name="organization" />
              </span>
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-baseline justify-between gap-2">
                <span className="min-w-0 flex-1 truncate text-[0.8125rem] font-medium">{room.name}</span>
                {state ? (
                  <span className="inline-flex shrink-0 items-center self-center text-[0.6875rem]" data-room-state={state}>
                    {state === 'working' ? (
                      <span aria-hidden="true" className="text-(--ui-accent)">
                        <GlyphSpinner />
                      </span>
                    ) : (
                      <Codicon
                        className={state === 'failed' ? 'text-destructive' : 'text-(--ui-accent)'}
                        name={state === 'failed' ? 'error' : 'bell-dot'}
                      />
                    )}
                    <span className="sr-only">
                      {state === 'working' ? labels.rowWorking : state === 'failed' ? labels.rowFailed : labels.rowNeedsYou}
                    </span>
                  </span>
                ) : null}
                {room.updatedAt ? (
                  <span className="shrink-0 text-[0.6875rem] text-(--ui-text-quaternary)">
                    {rowAge(room.updatedAt, t.sidebar.row)}
                  </span>
                ) : null}
              </span>
              <span className="flex min-w-0 items-center gap-1.5 text-xs text-(--ui-text-tertiary)">
                {room.members.length ? (
                  <AvatarStack
                    avatars={room.members.map(member => ({
                      key: member.member_id,
                      node: <RoomBotAvatar name={member.profile || member.handle} size={14} />
                    }))}
                    max={4}
                  />
                ) : null}
                <span className="min-w-0 truncate">{memberCount}</span>
              </span>
            </span>
          </RowButton>
        </ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem onSelect={onOpen}>{labels.openGroup}</ContextMenuItem>
          <ContextMenuSub>
            <ContextMenuSubTrigger>{b.sections.moveTo}</ContextMenuSubTrigger>
            <ContextMenuSubContent>
              {sections.map(section => (
                <ContextMenuItem
                  disabled={section.id === currentSectionId}
                  key={section.id}
                  onSelect={() => moveGatewayGroupToSection(room, section.id)}
                >
                  <Codicon className="mr-1.5" name="folder" />
                  {section.name}
                </ContextMenuItem>
              ))}
              {sections.length ? <ContextMenuSeparator /> : null}
              <ContextMenuItem onSelect={() => onNewSection(room)}>
                <Codicon className="mr-1.5" name="new-folder" />
                {b.sections.newSectionEllipsis}
              </ContextMenuItem>
              {currentSectionId ? (
                <ContextMenuItem onSelect={() => moveGatewayGroupToSection(room, null)}>
                  <Codicon className="mr-1.5" name="inbox" />
                  {b.sections.removeFromSection}
                </ContextMenuItem>
              ) : null}
            </ContextMenuSubContent>
          </ContextMenuSub>
          <ContextMenuSeparator />
          <ContextMenuItem onSelect={() => setConfirming(true)} variant="destructive">
            {group.disbandAction}
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>
      {confirming && (
        <ConfirmDialog
          busyLabel={labels.disbanding}
          confirmLabel={labels.disband}
          description={
            <span>
              {labels.disbandDescPrefix}
              <span className="font-medium text-foreground">{room.name}</span>
              {labels.disbandDescSuffix(room.members.length)}
            </span>
          }
          destructive
          doneLabel={labels.disbandDone}
          onClose={() => setConfirming(false)}
          onConfirm={() => disbandGatewayGroupRoom(room, labels.disbanded(room.name), labels)}
          open
          title={labels.disbandTitle}
        />
      )}
    </>
  )
}
