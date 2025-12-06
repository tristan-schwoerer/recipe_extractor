class RecipeExtractorCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity (todo entity)');
    }
    this.config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      this.render();
    }
  }

  render() {
    if (!this.config || !this._hass) {
      return;
    }

    const title = this.config.title || 'Recipe Extractor';
    const buttonText = this.config.button_text || 'Extract to List';
    const placeholder = this.config.placeholder || 'Enter recipe URL...';

    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
        }
        .card-header {
          font-size: 24px;
          font-weight: 500;
          margin-bottom: 16px;
          color: var(--primary-text-color);
        }
        .input-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .url-input {
          width: 100%;
          padding: 12px;
          font-size: 16px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background-color: var(--card-background-color);
          color: var(--primary-text-color);
          box-sizing: border-box;
        }
        .url-input:focus {
          outline: none;
          border-color: var(--primary-color);
        }
        .extract-button {
          padding: 12px 24px;
          font-size: 16px;
          font-weight: 500;
          color: var(--text-primary-color, white);
          background-color: var(--primary-color);
          border: none;
          border-radius: 4px;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        .extract-button:hover {
          background-color: var(--primary-color);
          filter: brightness(1.1);
        }
        .extract-button:active {
          filter: brightness(0.9);
        }
        .extract-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .status-message {
          margin-top: 12px;
          padding: 8px;
          border-radius: 4px;
          font-size: 14px;
        }
        .status-message.success {
          background-color: var(--success-color, #4caf50);
          color: white;
        }
        .status-message.error {
          background-color: var(--error-color, #f44336);
          color: white;
        }
        .status-message.info {
          background-color: var(--info-color, #2196f3);
          color: white;
        }
        .hidden {
          display: none;
        }
      </style>
      <ha-card>
        <div class="card-header">${title}</div>
        <div class="input-container">
          <input
            type="url"
            class="url-input"
            placeholder="${placeholder}"
            id="recipeUrl"
          />
          <button class="extract-button" id="extractButton">
            ${buttonText}
          </button>
          <div id="statusMessage" class="status-message hidden"></div>
        </div>
      </ha-card>
    `;

    this.content = true;
    this.setupListeners();
  }

  setupListeners() {
    const button = this.shadowRoot.getElementById('extractButton');
    const input = this.shadowRoot.getElementById('recipeUrl');
    const statusMessage = this.shadowRoot.getElementById('statusMessage');

    // Handle Enter key in input
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        button.click();
      }
    });

    button.addEventListener('click', async () => {
      const url = input.value.trim();

      if (!url) {
        this.showStatus('Please enter a recipe URL', 'error');
        return;
      }

      // Basic URL validation
      try {
        new URL(url);
      } catch (e) {
        this.showStatus('Please enter a valid URL', 'error');
        return;
      }

      button.disabled = true;
      this.showStatus('Extracting recipe...', 'info');

      try {
        await this._hass.callService('recipe_extractor', 'extract_to_list', {
          url: url,
          todo_entity: this.config.entity,
        });

        this.showStatus('Recipe extracted successfully!', 'success');
        input.value = '';

        // Clear success message after 3 seconds
        setTimeout(() => {
          statusMessage.classList.add('hidden');
        }, 3000);
      } catch (error) {
        console.error('Error extracting recipe:', error);
        this.showStatus('Failed to extract recipe: ' + error.message, 'error');
      } finally {
        button.disabled = false;
      }
    });
  }

  showStatus(message, type) {
    const statusMessage = this.shadowRoot.getElementById('statusMessage');
    statusMessage.textContent = message;
    statusMessage.className = 'status-message ' + type;
    statusMessage.classList.remove('hidden');
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement('recipe-extractor-card-editor');
  }

  static getStubConfig() {
    return {
      entity: 'todo.shopping_list',
      title: 'Recipe Extractor',
      button_text: 'Extract to List',
      placeholder: 'Enter recipe URL...',
    };
  }
}

// Define the custom card editor
class RecipeExtractorCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (!this.content) {
      this.render();
    }
  }

  set hass(hass) {
    this._hass = hass;
  }

  render() {
    this.innerHTML = `
      <div style="padding: 16px;">
        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 4px;">Entity (Todo List)*</label>
          <input
            type="text"
            id="entity"
            value="${this._config.entity || ''}"
            placeholder="todo.shopping_list"
            style="width: 100%; padding: 8px; box-sizing: border-box;"
          />
        </div>
        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 4px;">Title</label>
          <input
            type="text"
            id="title"
            value="${this._config.title || 'Recipe Extractor'}"
            style="width: 100%; padding: 8px; box-sizing: border-box;"
          />
        </div>
        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 4px;">Button Text</label>
          <input
            type="text"
            id="button_text"
            value="${this._config.button_text || 'Extract to List'}"
            style="width: 100%; padding: 8px; box-sizing: border-box;"
          />
        </div>
        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 4px;">Placeholder Text</label>
          <input
            type="text"
            id="placeholder"
            value="${this._config.placeholder || 'Enter recipe URL...'}"
            style="width: 100%; padding: 8px; box-sizing: border-box;"
          />
        </div>
      </div>
    `;

    this.content = true;
    this.setupEditorListeners();
  }

  setupEditorListeners() {
    const entity = this.querySelector('#entity');
    const title = this.querySelector('#title');
    const buttonText = this.querySelector('#button_text');
    const placeholder = this.querySelector('#placeholder');

    [entity, title, buttonText, placeholder].forEach((input) => {
      input.addEventListener('input', () => {
        this._config = {
          ...this._config,
          entity: entity.value,
          title: title.value,
          button_text: buttonText.value,
          placeholder: placeholder.value,
        };
        this.dispatchEvent(
          new CustomEvent('config-changed', {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          })
        );
      });
    });
  }
}

customElements.define('recipe-extractor-card', RecipeExtractorCard);
customElements.define('recipe-extractor-card-editor', RecipeExtractorCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'recipe-extractor-card',
  name: 'Recipe Extractor Card',
  description: 'A card to extract recipes from URLs and add ingredients to a todo list',
  preview: true,
  documentationURL: 'https://github.com/tristan-schwoerer/recipe_extractor',
});
