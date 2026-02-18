window.addEventListener('DOMContentLoaded', () => {
  // Adjust selector as needed for your theme
  const navDropdowns = document.querySelectorAll('.VPNavBarMenu .VPNavBarMenuGroup');
  navDropdowns.forEach(dropdown => {
    const items = dropdown.querySelectorAll('.VPNavBarMenuGroup .VPNavBarMenuGroupItems a');
    items.forEach(item => {
      item.addEventListener('click', function () {
        // Get the text of the clicked item (e.g., "v5.0.0")
        const versionText = this.textContent.replace(/\s*\(Current\)/, '');
        // Find the label element (the button or span showing the current version)
        const label = dropdown.querySelector('.VPNavBarMenuGroupButton span');
        if (label) label.textContent = versionText;
      });
    });
  });
});