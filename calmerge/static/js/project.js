;(function () {
  const toastOptions = { delay: 2000 }

  function createToast(message) {
    // Clone the template
    const element = htmx.find("[data-toast-template]").cloneNode(true)

    // Remove the data-toast-template attribute
    delete element.dataset.toastTemplate

    // Set the CSS class
    element.className += " " + message.tags

    // Set the text
    htmx.find(element, "[data-toast-body]").innerText = message.message

    // Add the new element to the container
    htmx.find("[data-toast-container]").appendChild(element)

    // Show the toast using Bootstrap's API
    const toast = new bootstrap.Toast(element, toastOptions)
    toast.show()
  }

  htmx.on("messages", (event) => {
    event.detail.value.forEach(createToast)
  })

  // Show all existsing toasts, except the template
  htmx.findAll(".toast:not([data-toast-template])").forEach((element) => {
    const toast = new bootstrap.Toast(element, toastOptions)
    toast.show()
  })
})()


function copyFileUrl(pk) {
  // Get the text field
  var copyText = document.getElementById("calendar_file_url"+ pk);

  // Select the text field
  copyText.select();
  copyText.setSelectionRange(0, 99999); // For mobile devices

   // Copy the text inside the text field
  navigator.clipboard.writeText(copyText.value);

  // Alert the copied text
  alert("Copied the text: " + copyText.value);
}
