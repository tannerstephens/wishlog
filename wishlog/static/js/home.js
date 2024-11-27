const listEntryTemplate = Handlebars.compile(`
    <div class="column is-one-third-desktop">
        <div class="card {{#if claimed}}is-claimed{{/if}}">
            <div class="card-image">
                {{#if link}}<a href="{{ link }}" target="_blank">{{/if}}
                <figure class="image is-4by3">
                    <img src="{{ image }}" loading="lazy">
                </figure>
                {{#if link}}</a>{{/if}}
            </div>
            <div class="card-content">
                <div class="content">
                    <h1 class="title is-3">
                        {{ title }}{{#if claimed}} - Claimed{{/if}}
                    </h1>
                    <h2 class="subtitle is-5">{{ price cost }}</h2>

                    <div class="filler"></div>

                    {{#if owner}}
                    <h3>Edit This Item</h3>
                    <div class="field">
                        <label class="label">Cost</label>
                        <div class="field-body">
                            <div class="field">
                                <div class="control">
                                    <input class="input" type="number" step="0.01" min="0" value="{{ cost }}" id="cost-{{ id }}">
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="field">
                        <label class="label">Desire</label>
                        <div class="field-body">
                            <div class="field">
                                <div class="control">
                                    <input class="input" type="number" step="1" value="{{ desire }}" id="desire-{{ id }}">
                                </div>
                            </div>
                        </div>
                    </div>
                    {{/if}}


                    <div class="field is-grouped">
                        {{#if link}}
                        <p class="control">
                            <a class="button is-warning" href="{{ link }}" target="_blank">Browse Item</a>
                        </p>
                        {{/if}}

                        {{#if owner}}
                            <p class="control">
                                <a class="button is-danger" id="delete-{{ id }}">Delete</a>
                            </p>
                        {{else}}
                            {{#if claimed}}
                                {{#if justclaimed}}
                                <p class="control">
                                    <a class="button is-danger" id="unclaim-{{ id }}">Unclaim</a>
                                </p>
                                {{/if}}
                            {{else}}
                            <p class="control">
                                <a class="button is-info" id="claim-{{ id }}">Mark As Purchased</a>
                            </p>
                            {{/if}}
                        {{/if}}
                    </div>

                </div>
            </div>
        </div>
    </div>
`)

Handlebars.registerHelper('price', function (cost) {
  return `\$${cost.toFixed(2)}`
})

window.onload = () => {
  const newFormParent = document.getElementById('new')
  const list = document.getElementById('list')

  const newItemForm = document.forms['newItemForm']
  const submitButton = document.getElementById('submit')
  const fileName = document.getElementById('fileName')

  const claimedSwitch = document.getElementById('claimedSwitch')

  const temp = document.getElementById('temp')

  const orderBy = document.getElementById('orderBy')

  let owner = false

  const appendItem = (item, replace) => {
    const div = document.createElement('div')
    div.innerHTML = listEntryTemplate({ ...item, owner }).trim()

    const element = div.firstChild

    if (replace instanceof HTMLDivElement) {
      replace.replaceWith(element)
    } else {
      list.prepend(element)
    }

    if (owner) {
      document.getElementById(`delete-${item.id}`).onclick = () => {
        fetch(`/api/items/${item.id}`, {
          method: 'DELETE'
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              element.remove()
            }
          })
      }

      const desireInput = document.getElementById(`desire-${item.id}`)
      const costInput = document.getElementById(`cost-${item.id}`)

      const patchItem = () => {
        fetch(`/api/items/${item.id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            desire: desireInput.value,
            cost: costInput.value
          })
        })
      }

      desireInput.onchange = patchItem
      costInput.onchange = patchItem
    } else if (item.justclaimed) {
      document.getElementById(`unclaim-${item.id}`).onclick = () => {
        fetch(`/api/items/${item.id}/unclaim`, {
          method: 'POST'
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              item.claimed = false
              item.justclaimed = false

              appendItem(item, element)
            } else {
              location.reload()
            }
          })
      }
    } else if (!item.claimed) {
      document.getElementById(`claim-${item.id}`).onclick = () => {
        fetch(`/api/items/${item.id}/claim`, {
          method: 'POST'
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              item.claimed = true
              item.justclaimed = true

              appendItem(item, element)
            } else {
              location.reload()
            }
          })
      }
    }
  }

  const loadAllItems = () => {
    temp.innerHTML = list.innerHTML
    list.innerHTML = ''

    const showClaimed = claimedSwitch.checked ? '&show_claimed' : ''
    const order_by_value = orderBy.value.split('-')
    const desc = order_by_value[1] == 'desc' ? '&desc' : ''

    fetch(`/api/items?order_by=${order_by_value[0]}${desc}${showClaimed}`)
      .then(response => response.json())
      .then(data => {
        data.items.reverse()
        data.items.forEach(appendItem)
        temp.innerHTML = ''
      })
  }

  fetch('/api/session')
    .then(response => response.json())
    .then(data => {
      if (data.user) {
        newFormParent.classList.remove('is-hidden')
        owner = true
      }

      loadAllItems(claimedSwitch.checked)
    })

  const createItem = item => {
    fetch('/api/items', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(item)
    })
      .then(response => response.json())
      .then(data => appendItem(data.item))
  }

  newItemForm.onsubmit = e => {
    e.preventDefault()

    if (submitButton.disabled) {
      return
    }

    const body = {
      title: newItemForm.title.value,
      desire: newItemForm.desire.value,
      cost: newItemForm.cost.value
    }

    if (newItemForm.link.value) {
      body.link = newItemForm.link.value
    }

    if (newItemForm.image.value) {
      const reader = new FileReader()

      reader.onload = () => {
        body.image = reader.result.split(',', 2)[1]
        createItem(body)
      }

      reader.readAsDataURL(newItemForm.image.files[0])
      return
    }

    createItem(body)
  }

  const setState = () => {
    submitButton.disabled =
      newItemForm.title.value.length == 0 ||
      newItemForm.cost.value.length == 0 ||
      newItemForm.desire.value.length == 0

    if (newItemForm.image.value) {
      fileName.innerText = newItemForm.image.files[0].name
    }
  }

  newItemForm.oninput = setState
  setState()

  claimedSwitch.onchange = () => {
    loadAllItems()
  }

  orderBy.onchange = () => {
    loadAllItems()
  }
}
