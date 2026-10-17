export interface RecentModel {
  model: string
  provider: string
}

export const modelId = (row: RecentModel) => `${row.provider}\t${row.model}`

/** Picker/cycle navigation history only; the gateway remains the model authority. */
export class ModelRecents {
  #sid: string | null = null
  #rows: RecentModel[] = []
  #cycling: Promise<void> = Promise.resolve()

  list(sid: string): readonly RecentModel[] {
    if (this.#sid !== sid) {
      this.#sid = sid
      this.#rows = []
    }

    return this.#rows
  }

  remember(sid: string, row: RecentModel) {
    this.list(sid)

    if (row.model && !this.#rows.some(item => modelId(item) === modelId(row))) {
      this.#rows.push(row)
    }
  }

  enqueue(run: () => Promise<void>): Promise<void> {
    this.#cycling = this.#cycling.then(run, run)

    return this.#cycling
  }
}
