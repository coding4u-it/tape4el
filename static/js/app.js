(() => {
  const search = document.querySelector("#element-search");
  const mode = document.querySelector("#color-mode");
  const oxidation = document.querySelector("#oxidation-value");
  const oxidationLabel = document.querySelector("#oxidation-label");
  const tiles = Array.from(document.querySelectorAll(".element-tile"));
  const emptyState = document.querySelector("#no-elements");

  if (!tiles.length) return;

  const applyFilters = () => {
    const term = search ? search.value.trim().toLocaleLowerCase("it") : "";
    const colorMode = mode ? mode.value : "type";
    const oxidationValue = oxidation ? oxidation.value : "0";
    document.querySelectorAll(".oxidation-control").forEach((control) => {
      control.hidden = colorMode !== "oxidation";
    });
    let visibleCount = 0;

    for (const tile of tiles) {
      const matchesSearch =
        !term ||
        tile.dataset.symbol.includes(term) ||
        tile.dataset.name.includes(term);
      tile.hidden = !matchesSearch;
      if (matchesSearch) visibleCount += 1;

      const colors = {
        type: tile.dataset.colorType,
        group: tile.dataset.colorGroup,
        period: tile.dataset.colorPeriod,
        block: tile.dataset.colorBlock,
        state: tile.dataset.colorState,
      };
      let color = colors[colorMode] || tile.dataset.colorType;
      if (colorMode === "oxidation") {
        const oxidationColors = JSON.parse(tile.dataset.colorOxidation || "{}");
        const values = (tile.dataset.oxidation || "").split(",");
        color = values.includes(oxidationValue)
          ? oxidationColors[oxidationValue] || tile.dataset.colorType
          : "#374151";
      }
      tile.style.setProperty("--tile-color", color);
      tile.classList.toggle(
        "not-selected",
        colorMode === "oxidation" &&
          !(tile.dataset.oxidation || "").split(",").includes(oxidationValue)
      );
    }

    if (emptyState) emptyState.hidden = visibleCount !== 0;
    if (oxidationLabel && oxidation) oxidationLabel.value = oxidationValue;
  };

  if (search) search.addEventListener("input", applyFilters);
  if (mode) mode.addEventListener("change", applyFilters);
  if (oxidation) oxidation.addEventListener("input", applyFilters);
  applyFilters();
})();
