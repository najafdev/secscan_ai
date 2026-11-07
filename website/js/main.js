/* ============================================================
   HackBot Website — JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  // ─── Navbar scroll effect ──────────────────────────────
  const navbar = document.getElementById('navbar');
  const backToTop = document.getElementById('backToTop');

  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    navbar.classList.toggle('scrolled', y > 40);
    backToTop.classList.toggle('visible', y > 500);
  });

  // ─── Back to top ───────────────────────────────────────
  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // ─── Mobile nav toggle ────────────────────────────────
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');

  navToggle.addEventListener('click', () => {
    navToggle.classList.toggle('active');
    navLinks.classList.toggle('active');
  });

  // Close menu on link click
  navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      navToggle.classList.remove('active');
      navLinks.classList.remove('active');
    });
  });

  // ─── Install tabs ─────────────────────────────────────
  const tabs = document.querySelectorAll('.install-tab');
  const panels = document.querySelectorAll('.install-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`tab-${target}`).classList.add('active');
    });
  });

  // ─── Copy buttons ─────────────────────────────────────
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const text = btn.dataset.copy;
      navigator.clipboard.writeText(text).then(() => {
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
          btn.textContent = orig;
          btn.classList.remove('copied');
        }, 2000);
      });
    });
  });

  // ─── Scroll fade-in animations ────────────────────────
  const animateElements = () => {
    const elements = document.querySelectorAll(
      '.feature-card, .screenshot-card, .mode-card, .intel-card, ' +
      '.provider-card, .tool-group, .qs-step, .author-card, .donate-card'
    );

    elements.forEach(el => {
      if (!el.classList.contains('fade-in')) {
        el.classList.add('fade-in');
      }
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );

    elements.forEach(el => observer.observe(el));
  };

  animateElements();

  // ─── Active nav highlighting ──────────────────────────
  const sections = document.querySelectorAll('section[id]');
  const navItems = document.querySelectorAll('.nav-links a[href^="#"]');

  const highlightNav = () => {
    const scrollY = window.scrollY + 100;

    sections.forEach(section => {
      const top = section.offsetTop;
      const height = section.offsetHeight;
      const id = section.getAttribute('id');

      if (scrollY >= top && scrollY < top + height) {
        navItems.forEach(a => {
          a.classList.remove('active-link');
          if (a.getAttribute('href') === `#${id}`) {
            a.classList.add('active-link');
          }
        });
      }
    });
  };

  window.addEventListener('scroll', highlightNav);
  highlightNav();

  // ─── Terminal typing effect (hero) ────────────────────
  const heroTerminal = document.querySelector('.hero-terminal .terminal-body code');
  if (heroTerminal) {
    heroTerminal.style.opacity = '0';
    setTimeout(() => {
      heroTerminal.style.transition = 'opacity .6s ease';
      heroTerminal.style.opacity = '1';
    }, 600);
  }

  // ─── Smooth section title reveal ──────────────────────
  document.querySelectorAll('.section-title, .section-desc').forEach(el => {
    el.classList.add('fade-in');
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
  });
});
