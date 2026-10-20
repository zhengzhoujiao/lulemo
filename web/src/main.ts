import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router";
import "./styles/global.css";

/** 禁止浏览器对输入框弹出历史/自动填充建议 */
function disableBrowserAutocomplete(root: ParentNode = document.body) {
  root.querySelectorAll("input, textarea, select").forEach((el) => {
    el.setAttribute("autocomplete", "off");
  });
}

const app = createApp(App).use(router);
app.mount("#app");
disableBrowserAutocomplete();

router.afterEach(() => {
  requestAnimationFrame(() => disableBrowserAutocomplete());
});

const autocompleteObserver = new MutationObserver((records) => {
  for (const record of records) {
    record.addedNodes.forEach((node) => {
      if (node instanceof HTMLElement) disableBrowserAutocomplete(node);
    });
  }
});
autocompleteObserver.observe(document.body, { childList: true, subtree: true });
