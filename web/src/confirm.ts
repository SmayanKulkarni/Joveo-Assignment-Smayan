// An in-page dialog, because a browser can silently suppress window.confirm and the click then does nothing.
export function ask(message: string, ok = "Delete"): Promise<boolean> {
  const dialog = document.createElement("dialog")
  dialog.className = "confirm-dialog"
  dialog.innerHTML = `<p></p><form method="dialog" class="actions"><button value="no" autofocus>Cancel</button><button value="yes" class="danger"></button></form>`
  dialog.querySelector("p")!.textContent = message
  dialog.querySelector(".danger")!.textContent = ok
  document.body.append(dialog)
  dialog.showModal()
  return new Promise((resolve) =>
    dialog.addEventListener("close", () => {
      resolve(dialog.returnValue === "yes")
      dialog.remove()
    }),
  )
}
