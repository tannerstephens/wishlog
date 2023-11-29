const listEntryTemplate = Handlebars.compile(`
    <div class="column is-one-third-desktop">
        <div class="card {{#if claimed}}is-claimed{{/if}}">
            <div class="card-image">
                <figure class="image is-4by3">
                    <img src="{{ image }}">
                </figure>
            </div>
            <div class="card-content">
                <div class="content">
                    {{#if claimed}}
                    <s>
                    {{/if}}
                    <b>{{ title }}</b>{{#if cost}} - \${{ cost }}{{/if}}
                    {{#if claimed}}
                    </s>&nbsp;<b>Claimed</b>
                    {{/if}}
                    <br>
                    <br>
                    <a class="button is-warning" href="{{ link }}" target="_blank">Browse Item</a>
                </div>
            </div>
            <footer class="card-footer">
                {{#if owner}}
                <a class="card-footer-item" id="delete-{{ id }}">Delete</a>
                {{else}}
                    {{#if claimed}}
                        {{#if justclaimed}}
                        <a class="card-footer-item" id="unclaim-{{ id }}">Unclaim</a>
                        {{else}}
                        <span class="card-footer-item">Claimed</span>
                        {{/if}}
                    {{else}}
                    <a class="card-footer-item" id="claim-{{ id }}">Mark As Purchased</a>
                    {{/if}}
                {{/if}}
            </footer>
        </div>
    </div>
`);

window.onload = () => {
    const newFormParent = document.getElementById('new');
    const list = document.getElementById('list');

    const newItemForm = document.forms['newItemForm'];
    const submitButton = document.getElementById('submit');
    const fileName = document.getElementById('fileName');

    const claimedSwitch = document.getElementById('claimedSwitch');

    const temp = document.getElementById('temp');

    let owner = false;

    const appendItem = (item, replace) => {
        const div = document.createElement('div');
        div.innerHTML = listEntryTemplate({...item, owner}).trim();

        const element = div.firstChild;

        if(replace instanceof HTMLDivElement){
            replace.replaceWith(element);
        } else {
            list.appendChild(element);
        }

        if(owner) {
            document.getElementById(`delete-${item.id}`).onclick = () => {
                fetch(`/api/items/${item.id}`, {
                    method: 'DELETE'
                })
                    .then(response => response.json())
                    .then(data => {
                        if(data.success) {
                            element.remove();
                        }
                    })
            }
        } else if(item.justclaimed) {
            document.getElementById(`unclaim-${item.id}`).onclick = () => {
                fetch(`/api/items/${item.id}/unclaim`, {
                    method: 'POST'
                })
                    .then(response => response.json())
                    .then(data => {
                        if(data.success) {
                            item.claimed = false;
                            item.justclaimed = false;

                            appendItem(item, element);
                        } else {
                            location.reload();
                        }
                    })
            }
        } else if(!item.claimed) {
            document.getElementById(`claim-${item.id}`).onclick = () => {
                fetch(`/api/items/${item.id}/claim`, {
                    method: 'POST'
                })
                    .then(response => response.json())
                    .then(data => {
                        if(data.success) {
                            item.claimed = true;
                            item.justclaimed = true;

                            appendItem(item, element);
                        } else {
                            location.reload();
                        }
                    })
            }
        }
    }

    const loadAllItems = claimed => {
        temp.innerHTML = list.innerHTML;
        list.innerHTML = '';

        const showClaimed = claimed ? 'show' : 'hide';

        fetch(`/api/items?claimed=${showClaimed}`)
            .then(response => response.json())
            .then(data => {
                data.items.forEach(appendItem);
                temp.innerHTML = '';
            });
    }

    fetch('/api/session')
        .then(response => response.json())
        .then(data => {
            if(data.user) {
                newFormParent.classList.remove('is-hidden');
                owner = true;
            }

            loadAllItems(claimedSwitch.checked);
        });


    const createItem = item => {
        fetch('/api/items', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(item)
        })
            .then(response => response.json())
            .then(data => appendItem(data.item));
    }

    newItemForm.onsubmit = e => {
        e.preventDefault();

        if(newItemForm.title.value.length == 0) {
            return
        }

        const body = {title: newItemForm.title.value};

        if(newItemForm.cost.value) {
            body.cost = newItemForm.cost.value;
        }

        if(newItemForm.link.value) {
            body.link = newItemForm.link.value;
        }

        if(newItemForm.image.value) {
            const reader = new FileReader();

            reader.onload = () => {
                body.image = reader.result.split(',',2)[1]
                createItem(body)
            }

            reader.readAsDataURL(newItemForm.image.files[0]);
            return
        }

        createItem(body);
    }

    const setState = () => {
        submitButton.disabled = (newItemForm.title.value.length == 0) || (newItemForm.cost.value.length == 0);

        if(newItemForm.image.value) {
            fileName.innerText = newItemForm.image.files[0].name;
        }
    }

    newItemForm.oninput = setState;
    setState();

    claimedSwitch.onchange = () => {
        console.log('hmm')
        loadAllItems(claimedSwitch.checked);
    }
}
