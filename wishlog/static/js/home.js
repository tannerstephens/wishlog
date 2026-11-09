const listEntryTemplate = Handlebars.compile(`
    <div class="column is-half-tablet is-one-third-desktop">
        <div class="card {{#if showAsClaimed}}is-claimed{{/if}}">
            <div class="card-image">
                {{#if link}}<a href="{{ link }}" target="_blank" rel="noopener noreferrer" tabindex="-1" aria-hidden="true">{{/if}}
                <figure class="image is-4by3">
                    {{#if image}}
                    <img src="{{ image }}" alt="{{ title }}" loading="lazy">
                    {{else}}
                    <span class="image-placeholder"><i class="fas fa-gift"></i></span>
                    {{/if}}
                </figure>
                {{#if link}}</a>{{/if}}
            </div>
            <div class="card-content">
                <div class="content">
                    <h3 class="title is-4 item-title">{{ title }}</h3>
                    <div class="item-meta">
                        <span class="subtitle is-5 has-text-weight-semibold">{{ price cost }}</span>
                        {{#if claimedByMe}}
                        <span class="tag is-success is-light">You claimed this</span>
                        {{else if showAsClaimed}}
                        <span class="tag is-danger is-light">Claimed</span>
                        {{/if}}
                    </div>

                    <div class="filler"></div>

                    {{#if owner}}
                    <div class="item-edit">
                    <div class="columns is-mobile is-2">
                        <div class="column">
                            <div class="field">
                                <label class="label" for="cost-{{ id }}">Cost</label>
                                <div class="control">
                                    <input class="input is-small" type="number" step="0.01" min="0" inputmode="decimal" value="{{ cost }}" id="cost-{{ id }}" data-field="cost">
                                </div>
                            </div>
                        </div>
                        <div class="column">
                            <div class="field">
                                <label class="label" for="desire-{{ id }}">Desire</label>
                                <div class="control">
                                    <input class="input is-small" type="number" step="1" inputmode="numeric" value="{{ desire }}" id="desire-{{ id }}" data-field="desire">
                                </div>
                            </div>
                        </div>
                    </div>
                    </div>
                    {{/if}}

                    <div class="buttons">
                        {{#if link}}
                        <a class="button is-warning is-light" href="{{ link }}" target="_blank" rel="noopener noreferrer">
                            <span>View item</span>
                            <span class="icon is-small"><i class="fas fa-external-link-alt"></i></span>
                        </a>
                        {{/if}}

                        {{#if owner}}
                            <button type="button" class="button is-danger is-outlined" data-action="delete">Delete</button>
                        {{else}}
                            {{#if claimed}}
                                {{#if claimedByMe}}
                                <button type="button" class="button is-danger is-light" data-action="unclaim">Unclaim</button>
                                {{/if}}
                            {{else}}
                            <button type="button" class="button is-info" data-action="claim">
                                <span class="icon is-small"><i class="fas fa-check"></i></span>
                                <span>Mark as purchased</span>
                            </button>
                            {{/if}}
                        {{/if}}
                    </div>

                </div>
            </div>
        </div>
    </div>
`);

Handlebars.registerHelper("price", function (cost) {
  return typeof cost === "number" ? `\$${cost.toFixed(2)}` : "";
});

// Items this browser has claimed, remembered so the visitor can still unclaim a
// claim after reloading. Storage can be unavailable (private mode, blocked
// site data); the page then works as before, just without remembering.
const myClaims = (() => {
  const key = "wishlog.myClaims";
  let ids = new Set();

  try {
    const stored = JSON.parse(localStorage.getItem(key));
    if (Array.isArray(stored)) {
      ids = new Set(stored.filter(Number.isInteger));
    }
  } catch (e) {}

  const save = () => {
    try {
      localStorage.setItem(key, JSON.stringify([...ids]));
    } catch (e) {}
  };

  return {
    has: (id) => ids.has(id),
    size: () => ids.size,
    add: (id) => {
      ids.add(id);
      save();
    },
    remove: (id) => {
      ids.delete(id);
      save();
    },
    // Forget items that were deleted or unclaimed by someone else
    keepOnly: (items) => {
      const stillMine = new Set(
        items
          .filter((item) => item.claimed && ids.has(item.id))
          .map((item) => item.id),
      );
      if (stillMine.size !== ids.size) {
        ids = stillMine;
        save();
      }
    },
  };
})();

window.onload = () => {
  const newFormParent = document.getElementById("new");
  const list = document.getElementById("list");

  const newItemForm = document.forms["newItemForm"];
  const submitButton = document.getElementById("submit");
  const fileName = document.getElementById("fileName");
  const formError = document.getElementById("formError");

  const claimedSwitch = document.getElementById("claimedSwitch");

  const temp = document.getElementById("temp");

  const orderBy = document.getElementById("orderBy");

  const empty = document.getElementById("empty");
  const emptyTitle = document.getElementById("emptyTitle");
  const emptyText = document.getElementById("emptyText");

  let owner = false;

  const updateEmptyState = () => {
    const isEmpty = list.children.length === 0;
    empty.classList.toggle("is-hidden", !isEmpty);
    if (!isEmpty) {
      return;
    }

    if (owner) {
      emptyTitle.textContent = "Your list is empty";
      emptyText.textContent =
        "Add the first thing you'd like using the form above.";
    } else if (claimedSwitch.checked) {
      emptyTitle.textContent = "There's nothing on the list yet";
      emptyText.textContent = "Check back later.";
    } else {
      emptyTitle.textContent = "Everything has been claimed";
      emptyText.textContent =
        "Nothing is left to buy right now. Check back later!";
    }
  };

  // Run a request from a button, showing a spinner and blocking double clicks
  const withLoading = (button, request) => {
    button.classList.add("is-loading");
    button.disabled = true;
    return request().finally(() => {
      button.classList.remove("is-loading");
      button.disabled = false;
    });
  };

  const postJson = (url, method) =>
    fetch(url, { method }).then((response) => response.json());

  const appendItem = (item, replace) => {
    const div = document.createElement("div");
    item.claimedByMe = !owner && item.claimed && myClaims.has(item.id);

    div.innerHTML = listEntryTemplate({
      ...item,
      owner,
      showAsClaimed: item.claimed && (!owner || claimedSwitch.checked),
    }).trim();

    const element = div.firstChild;

    if (replace instanceof HTMLDivElement) {
      replace.replaceWith(element);
    } else {
      list.prepend(element);
    }

    const button = (action) =>
      element.querySelector(`[data-action="${action}"]`);

    if (owner) {
      const deleteButton = button("delete");

      const deleteItem = () =>
        withLoading(deleteButton, () =>
          postJson(`/api/items/${item.id}`, "DELETE")
            .then((data) => {
              if (data.success) {
                element.remove();
                updateEmptyState();
              } else {
                alert(data.message || "Could not delete the item");
              }
            })
            .catch(() => alert("Could not reach the server, please try again")),
        );

      // First click arms the button ("Really?"), a second click deletes.
      let disarmTimer = null;
      const disarm = () => {
        clearTimeout(disarmTimer);
        delete deleteButton.dataset.armed;
        deleteButton.textContent = "Delete";
        deleteButton.classList.add("is-outlined");
      };

      deleteButton.onclick = () => {
        // Claimed items with surprises spoiled delete in one click, for quick
        // pruning of gifts already received after the event
        if (item.claimed && claimedSwitch.checked) {
          deleteItem();
          return;
        }

        // Every other delete, including claimed items while surprises are
        // hidden, uses the same two-step so it gives nothing away.
        if (deleteButton.dataset.armed) {
          disarm();
          deleteItem();
          return;
        }

        deleteButton.dataset.armed = "true";
        deleteButton.textContent = "Really?";
        deleteButton.classList.remove("is-outlined");
        disarmTimer = setTimeout(disarm, 3000);
      };
      deleteButton.onblur = disarm;

      const desireInput = element.querySelector('[data-field="desire"]');
      const costInput = element.querySelector('[data-field="cost"]');

      const patchItem = (input) => {
        input.classList.remove("is-saved", "is-danger");

        fetch(`/api/items/${item.id}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            desire: desireInput.value,
            cost: costInput.value,
          }),
        })
          .then((response) => response.json())
          .then((data) => {
            if (!data.success) {
              throw new Error(data.message);
            }

            item.cost = data.item.cost;
            item.desire = data.item.desire;
            element.querySelector(".item-meta .subtitle").textContent =
              Handlebars.helpers.price(item.cost);

            input.classList.add("is-saved");
            setTimeout(() => input.classList.remove("is-saved"), 1500);
          })
          .catch(() => input.classList.add("is-danger"));
      };

      desireInput.onchange = () => patchItem(desireInput);
      costInput.onchange = () => patchItem(costInput);
    } else if (item.claimedByMe) {
      const unclaimButton = button("unclaim");
      unclaimButton.onclick = () => {
        withLoading(unclaimButton, () =>
          postJson(`/api/items/${item.id}/unclaim`, "POST").then((data) => {
            if (data.success) {
              item.claimed = false;
              myClaims.remove(item.id);

              appendItem(item, element);
            } else {
              location.reload();
            }
          }),
        ).catch(() => alert("Could not reach the server, please try again"));
      };
    } else if (!item.claimed) {
      const claimButton = button("claim");
      claimButton.onclick = () => {
        withLoading(claimButton, () =>
          postJson(`/api/items/${item.id}/claim`, "POST").then((data) => {
            if (data.success) {
              item.claimed = true;
              myClaims.add(item.id);

              appendItem(item, element);
            } else {
              location.reload();
            }
          }),
        ).catch(() => alert("Could not reach the server, please try again"));
      };
    }
  };

  // Each load gets a number; only the most recent load is allowed to render, so
  // quickly toggling the switch or sort order can't render two lists at once.
  let latestLoad = 0;

  const loadAllItems = () => {
    const thisLoad = ++latestLoad;

    // Keep showing the old list while the new one loads. Skip if a previous
    // load already moved it to temp (the list is empty then).
    if (list.children.length > 0) {
      temp.innerHTML = list.innerHTML;
    }
    list.innerHTML = "";

    // A visitor with claims of their own needs claimed items too, so their
    // claims (and Unclaim buttons) survive a reload. Other claimed items are
    // filtered out below unless "Show claimed" is on.
    const includeMyClaims = !owner && myClaims.size() > 0;
    const fetchClaimed = owner || claimedSwitch.checked || includeMyClaims;
    const showClaimed = fetchClaimed ? "&show_claimed" : "";
    const orderByValue = orderBy.value.split("-");
    const desc = orderByValue[1] == "desc" ? "&desc" : "";

    fetch(`/api/items?order_by=${orderByValue[0]}${desc}${showClaimed}`)
      .then((response) => response.json())
      .then((data) => {
        if (thisLoad !== latestLoad) {
          return;
        }

        let items = data.items;
        if (!owner && fetchClaimed) {
          myClaims.keepOnly(items);
        }
        if (!owner && !claimedSwitch.checked) {
          items = items.filter(
            (item) => !item.claimed || myClaims.has(item.id),
          );
        }

        list.innerHTML = "";
        items.reverse();
        items.forEach((item) => appendItem(item));
        temp.innerHTML = "";
        updateEmptyState();
      });
  };

  fetch("/api/session")
    .then((response) => response.json())
    .then((data) => {
      if (data.user) {
        newFormParent.classList.remove("is-hidden");
        owner = true;
        document.querySelector('label[for="claimedSwitch"]').textContent =
          "Spoil my surprises";
        document.getElementById("heroSubtitle").textContent =
          "Add what you'd like. Claimed gifts stay hidden from you unless you spoil the surprise.";
        document.getElementById("logoutItem").classList.remove("is-hidden");
      }

      loadAllItems();
    });

  let submitting = false;

  const showFormError = (message) => {
    formError.textContent = message;
    formError.classList.remove("is-hidden");
  };

  const finishSubmit = () => {
    submitting = false;
    submitButton.classList.remove("is-loading");
    setState();
  };

  const createItem = (item) => {
    fetch("/api/items", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(item),
    })
      .then((response) => response.json())
      .then((data) => {
        if (!data.success) {
          showFormError(data.message || "Could not add the item");
          return;
        }

        appendItem(data.item);
        updateEmptyState();
        newItemForm.reset();
        resetAutofill();
        newItemForm.link.focus();
      })
      .catch(() =>
        showFormError("Could not reach the server, please try again"),
      )
      .finally(finishSubmit);
  };

  newItemForm.onsubmit = (e) => {
    e.preventDefault();

    if (submitButton.disabled || submitting) {
      return;
    }

    submitting = true;
    submitButton.disabled = true;
    submitButton.classList.add("is-loading");
    formError.classList.add("is-hidden");

    const body = {
      title: newItemForm.title.value,
      desire: newItemForm.desire.value,
      cost: newItemForm.cost.value,
    };

    if (newItemForm.link.value) {
      body.link = newItemForm.link.value;
    }

    if (newItemForm.image.value) {
      const reader = new FileReader();

      reader.onload = () => {
        body.image = reader.result.split(",", 2)[1];
        createItem(body);
      };
      reader.onerror = () => {
        showFormError("Could not read the selected image");
        finishSubmit();
      };

      reader.readAsDataURL(newItemForm.image.files[0]);
      return;
    }

    createItem(body);
  };

  const setState = () => {
    submitButton.disabled =
      submitting ||
      newItemForm.title.value.trim().length == 0 ||
      newItemForm.cost.value.length == 0 ||
      newItemForm.desire.value.length == 0;

    fileName.textContent = newItemForm.image.value
      ? newItemForm.image.files[0].name
      : "No image";
  };

  // Autofill: "Fill in details" fetches the linked page (through the server,
  // since the browser can't read other sites) and fills in the blank fields
  // from it. Fields the owner typed in themselves are never overwritten, but
  // values filled in from an earlier link are replaced by the new link's.
  const fillButton = document.getElementById("fillFromLink");
  const linkHelp = document.getElementById("linkHelp");
  let autofilled = {};
  let imageAutofilled = false;
  let latestPreview = 0;
  let previewing = false;

  const setFillButtonState = () => {
    fillButton.disabled = previewing || !newItemForm.link.value.trim();
    fillButton.classList.toggle("is-loading", previewing);
  };

  const stopPreview = () => {
    latestPreview++;
    previewing = false;
    setFillButtonState();
  };

  const resetAutofill = () => {
    stopPreview();
    autofilled = {};
    imageAutofilled = false;
    linkHelp.textContent = "";
  };

  const fillField = (name, value) => {
    const input = newItemForm[name];
    if (value === null || value === undefined || value === "") {
      return false;
    }
    if (input.value && input.value !== autofilled[name]) {
      return false;
    }
    input.value = value;
    autofilled[name] = input.value;
    return true;
  };

  const fillImage = (preview) => {
    const input = newItemForm.image;
    if (!preview.image || (input.value && !imageAutofilled)) {
      return false;
    }
    try {
      const bytes = Uint8Array.from(atob(preview.image), (c) => c.charCodeAt(0));
      const file = new File([bytes], preview.image_name || "image", {
        type: preview.image_type || "",
      });
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
    } catch (e) {
      // Older browsers can't set a file input; the owner can still pick one
      return false;
    }
    imageAutofilled = true;
    return true;
  };

  const LOOKUP_FAILED = "Couldn't find details for this link.";

  const describeFilled = (filled) => {
    if (filled.length === 0) {
      return "";
    }
    if (filled.length === 1) {
      return filled[0];
    }
    return `${filled.slice(0, -1).join(", ")} and ${filled[filled.length - 1]}`;
  };

  const previewLink = () => {
    const link = newItemForm.link.value.trim();
    if (!link || previewing) {
      return;
    }
    const thisPreview = ++latestPreview;

    previewing = true;
    setFillButtonState();
    linkHelp.textContent = "Looking up the details…";

    fetch("/api/link-preview", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url: link }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (thisPreview !== latestPreview) {
          return;
        }
        // Why a lookup failed (blocked, bot check, unreachable) is nothing
        // the owner can act on, so every failure gets the same short note
        if (!data.success) {
          linkHelp.textContent = LOOKUP_FAILED;
          return;
        }

        const preview = data.preview;
        const found = [];
        const filled = [];
        const note = (isFound, didFill, label) => {
          if (isFound) found.push(label);
          if (didFill) filled.push(label);
        };

        note(!!preview.title, fillField("title", preview.title), "title");
        note(
          typeof preview.cost === "number",
          typeof preview.cost === "number" &&
            fillField("cost", preview.cost.toFixed(2)),
          "cost",
        );
        note(!!preview.image, fillImage(preview), "image");
        setState();

        if (found.length === 0) {
          linkHelp.textContent = LOOKUP_FAILED;
        } else if (filled.length === 0) {
          linkHelp.textContent = "Kept what you already entered.";
        } else {
          const missing = ["title", "cost"].filter((f) => !found.includes(f));
          linkHelp.textContent =
            `Filled in the ${describeFilled(filled)} from the page. Check before adding.` +
            (missing.length
              ? ` Couldn't find the ${describeFilled(missing)}.`
              : "");
        }
      })
      .catch(() => {
        if (thisPreview === latestPreview) {
          linkHelp.textContent = LOOKUP_FAILED;
        }
      })
      .finally(() => {
        if (thisPreview === latestPreview) {
          previewing = false;
          setFillButtonState();
        }
      });
  };

  fillButton.addEventListener("click", previewLink);
  newItemForm.link.addEventListener("input", () => {
    // Cleared link: cancel any lookup, but keep track of what was autofilled
    // so a different link filled in next can still replace those values
    if (!newItemForm.link.value.trim()) {
      stopPreview();
      linkHelp.textContent = "";
    }
    setFillButtonState();
  });
  // An image the owner picks themselves is theirs to keep
  newItemForm.image.addEventListener("change", () => {
    imageAutofilled = false;
  });

  newItemForm.oninput = setState;
  newItemForm.onchange = setState;
  setState();

  claimedSwitch.onchange = () => {
    loadAllItems();
  };

  orderBy.onchange = () => {
    loadAllItems();
  };

  document.getElementById("logout").onclick = () => {
    fetch("/api/session", { method: "DELETE" }).finally(() => {
      window.location = "/";
    });
  };
};
