/* Caitlin Carney Tattoo: everything that moves.
   Loads after gsap.min.js, ScrollTrigger.min.js and lenis.min.js (all optional: without them the page
   still reveals, scrolls and opens photos, just plainly). Everything switches off for reduced motion. */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var hasGsap = typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined';
  var home = document.body.classList.contains('home');
  // Phones, touch screens and small machines get the light version: the same page, fewer moving parts
  var lite = !fine || window.innerWidth < 768 || (navigator.hardwareConcurrency || 8) < 4;
  if (hasGsap) { gsap.registerPlugin(ScrollTrigger); }
  window.CCT = window.CCT || {};
  window.CCT.lite = lite;

  /* 1. Smooth scrolling */
  var lenis = null;
  if (!reduce && !lite && typeof Lenis !== 'undefined') {
    try {
      lenis = new Lenis({ lerp: 0.085, smoothWheel: true, anchors: true });
      if (hasGsap) {
        lenis.on('scroll', ScrollTrigger.update);
        gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
        gsap.ticker.lagSmoothing(0);
      } else {
        var rafLenis = function (t) { lenis.raf(t); requestAnimationFrame(rafLenis); };
        requestAnimationFrame(rafLenis);
      }
    } catch (e) { lenis = null; }
  }
  window.CCT.lenis = lenis;

  /* 2. Header turns glassy once scrolled */
  var bar = document.getElementById('bar');
  var onScrollY = function (y) { if (bar) { bar.classList.toggle('stuck', y > 40); } };
  if (lenis) { lenis.on('scroll', function (e) { onScrollY(e.scroll); }); }
  else { window.addEventListener('scroll', function () { onScrollY(window.scrollY || 0); }, { passive: true }); }
  onScrollY(window.scrollY || 0);

  /* 3. Reveals and parallax */
  var reveals = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
  var layers = Array.prototype.slice.call(document.querySelectorAll('[data-depth]'));
  if (reduce) {
    reveals.forEach(function (el) { el.classList.add('in'); });
  } else if (hasGsap) {
    // GSAP drives the entrances, so the CSS reveal is switched off and its transition removed
    reveals.forEach(function (el) { el.style.transition = 'none'; el.classList.add('in'); });
    var kinds = document.querySelectorAll('.kinds .kind');
    var tiles = document.querySelectorAll('.gallery figure');
    var special = Array.prototype.slice.call(kinds).concat(Array.prototype.slice.call(tiles));
    reveals.forEach(function (el) {
      if (special.indexOf(el) !== -1) { return; }
      gsap.from(el, { y: 44, opacity: 0, duration: 1.1, ease: 'power3.out',
        scrollTrigger: { trigger: el, start: 'top 90%', once: true } });
    });
    if (kinds.length) {
      gsap.from(kinds, lite
        ? { y: 60, opacity: 0, stagger: 0.1, duration: 0.9, ease: 'power3.out', scrollTrigger: { trigger: '.kinds', start: 'top 85%', once: true } }
        : { y: 140, z: -300, rotationY: 70, rotationX: 18, opacity: 0, transformPerspective: 900, transformOrigin: '50% 100%',
            stagger: 0.14, duration: 1.5, ease: 'power3.out', scrollTrigger: { trigger: '.kinds', start: 'top 82%', once: true } });
    }
    document.querySelectorAll('.gallery').forEach(function (g) {
      var figs = g.querySelectorAll('figure');
      if (!figs.length) { return; }
      gsap.from(figs, lite
        ? { y: 50, opacity: 0, stagger: { each: 0.06 }, duration: 0.9, ease: 'power3.out', scrollTrigger: { trigger: g, start: 'top 88%', once: true } }
        : { y: 120, z: -200, rotationX: 45, opacity: 0, transformPerspective: 800, transformOrigin: '50% 100%',
            stagger: { each: 0.08 }, duration: 1.3, ease: 'power3.out', scrollTrigger: { trigger: g, start: 'top 85%', once: true } });
    });
    // Layers at their own depth, the hero handled by hand below
    layers.forEach(function (el) {
      if (el.closest('.hero')) { return; }
      var d = (parseFloat(el.getAttribute('data-depth')) || 0) * (lite ? 0.5 : 1);
      var box = el.closest('section, .band') || el;
      gsap.fromTo(el, { y: d * 420 }, { y: -d * 420, ease: 'none',
        scrollTrigger: { trigger: box, start: 'top bottom', end: 'bottom top', scrub: true } });
    });
    // The hero scrolls away in three layers, the arches swinging apart (flat on the light version)
    if (home) {
      var heroST = { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true };
      if (lite) {
        gsap.to('.hero-copy', { y: -80, opacity: 0.2, ease: 'none', scrollTrigger: heroST });
        gsap.to('.hero-art .big', { y: -120, ease: 'none', scrollTrigger: heroST });
        gsap.to('.hero-art .small', { y: -200, ease: 'none', scrollTrigger: heroST });
      } else {
        gsap.to('.hero-copy', { y: -120, z: -200, opacity: 0.1, transformPerspective: 1000, ease: 'none', scrollTrigger: heroST });
        gsap.to('.hero-art .big', { y: -200, x: 80, rotationY: -34, rotationX: 16, z: -120, transformPerspective: 1100, ease: 'none', scrollTrigger: heroST });
        gsap.to('.hero-art .small', { y: -380, x: -60, rotationY: 38, rotationX: 10, z: 60, transformPerspective: 1100, ease: 'none', scrollTrigger: heroST });
      }
      gsap.to('.ghost-arch', { y: lite ? 120 : 220, ease: 'none', scrollTrigger: heroST });
      // The faith band: the photo eases in from a zoom, the words read themselves as you scroll
      var band = document.querySelector('.band');
      if (band) {
        gsap.fromTo('.band img.bg', { scale: 1.35 }, { scale: 1, ease: 'none',
          scrollTrigger: { trigger: band, start: 'top bottom', end: 'bottom top', scrub: true } });
        var quote = band.querySelector('blockquote');
        if (quote) {
          var words = [];
          Array.prototype.slice.call(quote.childNodes).forEach(function (node) {
            if (node.nodeType !== 3 || !node.textContent.trim()) { return; }
            var frag = document.createDocumentFragment();
            node.textContent.split(/(\s+)/).forEach(function (part) {
              if (!part) { return; }
              if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(' ')); return; }
              var w = document.createElement('span'); w.className = 'w'; w.textContent = part;
              frag.appendChild(w); words.push(w);
            });
            quote.replaceChild(frag, node);
          });
          if (words.length) {
            gsap.fromTo(words, { opacity: 0.12, y: 8 }, { opacity: 1, y: 0, stagger: 0.03, ease: 'none',
              scrollTrigger: { trigger: band, start: 'top 75%', end: 'center 45%', scrub: true } });
          }
        }
      }
    }
    // Subject pages: the heading photo drifts up a little as you read
    var headArt = document.querySelector('.head-art');
    if (headArt) {
      gsap.to(headArt, { y: -70, rotationY: -8, transformPerspective: 1000, ease: 'none',
        scrollTrigger: { trigger: '.page-head', start: 'top top', end: 'bottom top', scrub: true } });
    }
    // The ticker leans with the speed of the scroll
    var tick = document.querySelector('.ticker div');
    if (tick && lenis) {
      var skew = gsap.quickTo(tick, 'skewX', { duration: 0.4, ease: 'power3' });
      lenis.on('scroll', function (e) { skew(Math.max(-14, Math.min(14, e.velocity * 0.35))); });
    }
  } else if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('in'); });
  }
  // Parallax without GSAP: the old way, one frame at a time
  if (!reduce && !hasGsap && layers.length) {
    var ticking = false;
    var frame = function () {
      ticking = false;
      var vh = window.innerHeight;
      layers.forEach(function (el) {
        var r = el.getBoundingClientRect();
        var centre = r.top + r.height / 2 - vh / 2;
        var d = parseFloat(el.getAttribute('data-depth')) || 0;
        el.style.transform = 'translate3d(0,' + (-centre * d).toFixed(1) + 'px,0)';
      });
    };
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }, { passive: true });
    window.addEventListener('resize', frame);
    frame();
  }

  /* 4. Frames tilt under the hand */
  if (fine && !reduce) {
    document.querySelectorAll('.tilt').forEach(function (el) {
      if (hasGsap) {
        // The frame turns towards the hand and lifts; the photo inside slides the other way, so the
        // frame reads as a window with depth behind it
        var rx = gsap.quickTo(el, 'rotationX', { duration: 0.6, ease: 'power3' });
        var ry = gsap.quickTo(el, 'rotationY', { duration: 0.6, ease: 'power3' });
        var rz = gsap.quickTo(el, 'z', { duration: 0.6, ease: 'power3' });
        var pic = el.querySelector('img');
        var ix = pic ? gsap.quickTo(pic, 'x', { duration: 0.7, ease: 'power3' }) : null;
        var iy = pic ? gsap.quickTo(pic, 'y', { duration: 0.7, ease: 'power3' }) : null;
        gsap.set(el, { transformPerspective: 900 });
        if (pic) { gsap.set(pic, { scale: 1.08 }); }
        el.addEventListener('mousemove', function (e) {
          var r = el.getBoundingClientRect();
          var px = (e.clientX - r.left) / r.width - 0.5;
          var py = (e.clientY - r.top) / r.height - 0.5;
          ry(px * 22); rx(-py * 18); rz(40);
          if (ix) { ix(-px * 22); iy(-py * 18); }
        });
        el.addEventListener('mouseleave', function () { ry(0); rx(0); rz(0); if (ix) { ix(0); iy(0); } });
      } else {
        el.addEventListener('mousemove', function (e) {
          var r = el.getBoundingClientRect();
          var px = (e.clientX - r.left) / r.width - 0.5;
          var py = (e.clientY - r.top) / r.height - 0.5;
          el.style.setProperty('--ry', (px * 10).toFixed(2) + 'deg');
          el.style.setProperty('--rx', (-py * 8).toFixed(2) + 'deg');
        });
        el.addEventListener('mouseleave', function () { el.style.setProperty('--ry', '0deg'); el.style.setProperty('--rx', '0deg'); });
      }
    });
  }

  /* 5. Dust: a few dozen slow specks wherever a .dust box sits */
  document.querySelectorAll('.dust').forEach(function (box) {
    for (var i = 0; i < (lite ? 10 : 36); i++) {
      var s = document.createElement('i');
      s.style.left = (Math.random() * 100) + '%';
      s.style.top = (40 + Math.random() * 60) + '%';
      s.style.setProperty('--t', (12 + Math.random() * 16) + 's');
      s.style.setProperty('--d', (-Math.random() * 20) + 's');
      s.style.setProperty('--x', ((Math.random() - 0.5) * 120) + 'px');
      s.style.setProperty('--o', (0.25 + Math.random() * 0.5).toFixed(2));
      var size = (1.5 + Math.random() * 2.5).toFixed(1);
      s.style.width = size + 'px'; s.style.height = size + 'px';
      box.appendChild(s);
    }
  });

  /* 6. The lamp follows the pointer; on the home page it sweeps in from the left once */
  var lamp = document.getElementById('lamp');
  var sweeping = false;
  if (lamp && fine && !reduce) {
    if (home) {
      sweeping = true;
      lamp.style.transition = 'none';
      lamp.style.transform = 'translate(' + (-window.innerWidth * 0.9) + 'px,' + (window.innerHeight * 0.15) + 'px)';
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        lamp.style.transition = 'transform 2.8s cubic-bezier(0.22, 0.61, 0.36, 1)';
        lamp.style.transform = 'translate(' + (window.innerWidth * 0.3) + 'px,' + (-window.innerHeight * 0.2) + 'px)';
        setTimeout(function () { sweeping = false; lamp.style.transition = ''; }, 2900);
      }); });
    }
    document.addEventListener('mousemove', function (e) {
      if (sweeping) { return; }
      lamp.style.transform = 'translate(' + (e.clientX - window.innerWidth * 0.45) + 'px,' + (e.clientY - window.innerHeight * 0.45) + 'px)';
    });
  } else if (lamp) {
    lamp.style.transform = 'translate(' + (window.innerWidth * 0.3) + 'px,' + (window.innerHeight * 0.1) + 'px)';
  }

  /* 7. A cursor of its own: a dot, and a ring that lags behind and opens over anything you can press */
  if (fine && !reduce && hasGsap) {
    var dot = document.createElement('div'); dot.className = 'cursor-dot';
    var ring = document.createElement('div'); ring.className = 'cursor-ring';
    document.body.appendChild(dot); document.body.appendChild(ring);
    document.body.classList.add('has-cursor');
    var dx = gsap.quickTo(dot, 'x', { duration: 0.08, ease: 'power2' }), dy = gsap.quickTo(dot, 'y', { duration: 0.08, ease: 'power2' });
    var rx2 = gsap.quickTo(ring, 'x', { duration: 0.4, ease: 'power3' }), ry2 = gsap.quickTo(ring, 'y', { duration: 0.4, ease: 'power3' });
    var shown = false;
    document.addEventListener('mousemove', function (e) {
      dx(e.clientX); dy(e.clientY); rx2(e.clientX); ry2(e.clientY);
      if (!shown) { shown = true; gsap.to([dot, ring], { opacity: 1, duration: 0.3 }); }
    });
    document.addEventListener('mouseleave', function () { gsap.to([dot, ring], { opacity: 0, duration: 0.3 }); shown = false; });
    var over = function (on) { ring.classList.toggle('on', on); dot.classList.toggle('on', on); };
    document.addEventListener('mouseover', function (e) { over(!!e.target.closest('a, button, .tilt, summary, label')); });
    document.addEventListener('mousedown', function () { ring.classList.add('down'); });
    document.addEventListener('mouseup', function () { ring.classList.remove('down'); });
  }

  /* 8. Buttons pull towards the pointer */
  if (fine && !reduce && hasGsap) {
    document.querySelectorAll('.btn').forEach(function (btn) {
      var mx = gsap.quickTo(btn, 'x', { duration: 0.35, ease: 'power3' });
      var my = gsap.quickTo(btn, 'y', { duration: 0.35, ease: 'power3' });
      btn.addEventListener('mousemove', function (e) {
        var r = btn.getBoundingClientRect();
        mx((e.clientX - (r.left + r.width / 2)) * 0.28);
        my((e.clientY - (r.top + r.height / 2)) * 0.28);
      });
      btn.addEventListener('mouseleave', function () { gsap.to(btn, { x: 0, y: 0, duration: 0.7, ease: 'elastic.out(1, 0.45)' }); });
    });
  }

  /* 8b. Photos ripple like liquid when the pointer lands on them, and a sheen follows the hand */
  var liquidAnim = document.getElementById('liquid-anim');
  if (fine && !reduce && liquidAnim && typeof liquidAnim.beginElement === 'function') {
    var rippling = null, rippleTimer = 0;
    var ripple = function (img) {
      if (rippling) { rippling.style.filter = ''; }
      rippling = img;
      img.style.filter = 'url(#liquid)';
      try { liquidAnim.beginElement(); } catch (e) {}
      clearTimeout(rippleTimer);
      rippleTimer = setTimeout(function () { if (rippling === img) { img.style.filter = ''; rippling = null; } }, 1150);
    };
    document.querySelectorAll('.gallery figure, .arch').forEach(function (fig) {
      var img = fig.querySelector('img');
      if (!img) { return; }
      var sheen = document.createElement('i');
      sheen.className = 'sheen';
      fig.appendChild(sheen);
      fig.addEventListener('mouseenter', function () { ripple(img); });
      fig.addEventListener('mousemove', function (e) {
        var r = fig.getBoundingClientRect();
        sheen.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
        sheen.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
      });
    });
  }

  /* 9. A gallery tile opens full size: its caption, arrows, and the way to book */
  var opens = Array.prototype.slice.call(document.querySelectorAll('.gallery a.open'));
  var dlg = document.createElement('dialog');
  if (opens.length && typeof dlg.showModal === 'function') {
    dlg.className = 'lightbox';
    dlg.innerHTML = '<figure><img alt=""><figcaption></figcaption></figure>' +
      '<div class="lb-bar"><a class="btn primary" href="/#book">Get a quote</a><span class="lb-count"></span></div>' +
      '<button class="lb-prev" type="button" aria-label="Previous photo">&#8249;</button>' +
      '<button class="lb-next" type="button" aria-label="Next photo">&#8250;</button>' +
      '<button class="lb-close" type="button" aria-label="Close">&#215;</button>';
    document.body.appendChild(dlg);
    var lbImg = dlg.querySelector('img'), lbCap = dlg.querySelector('figcaption'), lbCount = dlg.querySelector('.lb-count'), cur = 0;
    var show = function (i) {
      cur = (i + opens.length) % opens.length;
      var src = opens[cur].querySelector('img');
      lbImg.src = opens[cur].getAttribute('href');
      lbImg.alt = src ? src.alt : '';
      lbCap.textContent = src ? src.alt : '';
      lbCount.textContent = (cur + 1) + ' of ' + opens.length;
    };
    opens.forEach(function (a, i) { a.addEventListener('click', function (e) { e.preventDefault(); show(i); dlg.showModal(); if (lenis) { lenis.stop(); } }); });
    dlg.querySelector('.lb-prev').addEventListener('click', function () { show(cur - 1); });
    dlg.querySelector('.lb-next').addEventListener('click', function () { show(cur + 1); });
    dlg.querySelector('.lb-close').addEventListener('click', function () { dlg.close(); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) { dlg.close(); } });
    dlg.addEventListener('keydown', function (e) { if (e.key === 'ArrowLeft') { show(cur - 1); } if (e.key === 'ArrowRight') { show(cur + 1); } });
    var tx = 0;
    dlg.addEventListener('touchstart', function (e) { tx = e.changedTouches[0].clientX; }, { passive: true });
    dlg.addEventListener('touchend', function (e) { var dxx = e.changedTouches[0].clientX - tx; if (dxx > 50) { show(cur - 1); } else if (dxx < -50) { show(cur + 1); } }, { passive: true });
    dlg.addEventListener('close', function () { lbImg.removeAttribute('src'); opens[cur].focus(); if (lenis) { lenis.start(); } });
  }

  /* 10. The brush that paints the line under her name. The 3D version (brush3d.js) takes over on the
         home page when WebGL is there; this flat one is the fallback, started by that script if it
         cannot run, or here when it is not loaded at all. */
  var brush = document.getElementById('brush');
  var ink = document.getElementById('stencil-path');
  window.CCT.startFlatBrush = function () {
    if (!brush || !ink || reduce || !brush.animate || !window.CSS || !CSS.supports('offset-path', 'path("M0 0 L1 1")')) { return; }
    if (brush.dataset.started) { return; }
    brush.dataset.started = '1';
    var art = brush.querySelector('svg.art');
    var sil = art.cloneNode(true);
    sil.setAttribute('class', 'sil');
    brush.insertBefore(sil, art);
    var lineSvg = ink.ownerSVGElement;
    var host = brush.offsetParent || lineSvg.parentNode;
    var endX = 0, endY = 0;
    var place = function () {
      var r = lineSvg.getBoundingClientRect();
      var hr = host.getBoundingClientRect();
      var s = r.width / 600;
      var top = r.top - hr.top + (r.height - 18 * s) / 2;
      var d = ink.getAttribute('d').replace(/-?\d*\.?\d+/g, function (n) { return (parseFloat(n) * s).toFixed(2); });
      brush.style.left = (r.left - hr.left) + 'px';
      brush.style.top = top + 'px';
      brush.style.offsetPath = 'path("' + d + '")';
      var h = Math.max(130, Math.min(340, r.width * 0.5));
      brush.style.height = h + 'px';
      brush.style.width = (h * 120 / 320) + 'px';
      endX = r.left - hr.left + 598 * s;
      endY = top + 8 * s;
    };
    place();
    window.addEventListener('resize', place);
    var t0 = 0;
    try { var a = ink.getAnimations ? ink.getAnimations()[0] : null; if (a && a.currentTime !== null) { t0 = a.currentTime; } } catch (e) {}
    var P = 'perspective(900px) ';
    var swoop = 'cubic-bezier(0.2, 0.8, 0.2, 1)';
    brush.animate([
      { offset: 0, opacity: 0, transform: 'translate(40vw, -75vh) ' + P + 'rotateY(70deg) rotateX(20deg) rotate(-40deg) scale(3)', filter: 'blur(6px)' },
      { offset: 0.5, opacity: 1, filter: 'blur(2px)' },
      { offset: 0.88, transform: 'translate(0px, 0px) ' + P + 'rotateY(0deg) rotateX(32deg) rotate(28deg) scale(0.96)', filter: 'blur(0px)' },
      { offset: 1, opacity: 1, transform: 'translate(0px, 0px) ' + P + 'rotateY(0deg) rotateX(32deg) rotate(28deg) scale(1)', filter: 'blur(0px)' }
    ], { duration: 800, delay: 300 - t0, easing: swoop, fill: 'forwards' });
    brush.animate([
      { offset: 0, offsetDistance: '0%', transform: P + 'rotateY(0deg) rotateX(32deg) rotate(28deg) scale(1)' },
      { offset: 0.5, transform: P + 'rotateY(0deg) rotateX(30deg) rotate(33deg) scale(1)' },
      { offset: 1, offsetDistance: '100%', transform: P + 'rotateY(0deg) rotateX(32deg) rotate(26deg) scale(1)' }
    ], { duration: 1600, delay: 1100 - t0, easing: 'ease-out', fill: 'forwards' });
    brush.animate([
      { offset: 0, offsetDistance: '100%', transform: 'translate(0px, 0px) ' + P + 'rotateY(0deg) rotateX(32deg) rotate(26deg) scale(1)', opacity: 1, filter: 'blur(0px)' },
      { offset: 1, offsetDistance: '100%', transform: 'translate(120px, -240px) ' + P + 'rotateY(-40deg) rotateX(10deg) rotate(4deg) scale(1.6)', opacity: 0, filter: 'blur(4px)' }
    ], { duration: 750, delay: 2700 - t0, easing: 'cubic-bezier(0.4, 0, 0.9, 0.5)', fill: 'forwards' });
    sil.animate([
      { transform: 'translate(170px, 150px) scale(1.3)', filter: 'blur(30px)', opacity: 0.2 },
      { transform: 'translate(16px, 12px) scale(1)', filter: 'blur(6px)', opacity: 0.5 }
    ], { duration: 800, delay: 300 - t0, easing: swoop, fill: 'forwards' });
    sil.animate([
      { transform: 'translate(16px, 12px) scale(1)', filter: 'blur(6px)', opacity: 0.5 },
      { transform: 'translate(150px, 120px) scale(1.35)', filter: 'blur(32px)', opacity: 0 }
    ], { duration: 750, delay: 2700 - t0, easing: 'ease-in', fill: 'forwards' });
    window.CCT.lightName(t0);
    window.CCT.flecks(host, endX, endY, t0);
  };
  window.CCT.lightName = function (t0) {
    var name = document.querySelector('.hero h1');
    if (name) { setTimeout(function () { name.classList.add('lit'); }, Math.max(0, 1050 - t0)); }
  };
  window.CCT.flecks = function (host, endX, endY, t0) {
    setTimeout(function () {
      for (var i = 0; i < 9; i++) {
        var f = document.createElement('i');
        f.className = 'fleck';
        var size = 3 + Math.random() * 6;
        f.style.width = size + 'px'; f.style.height = size + 'px';
        f.style.left = endX + 'px'; f.style.top = endY + 'px';
        host.appendChild(f);
        var ang = -0.2 - Math.random() * 1.3;
        var dist = 60 + Math.random() * 160;
        f.animate([
          { transform: 'translate(0px, 0px) scale(1)', opacity: 0.9 },
          { transform: 'translate(' + (Math.cos(ang) * dist).toFixed(0) + 'px, ' + (Math.sin(ang) * dist + 40).toFixed(0) + 'px) scale(0.2)', opacity: 0 }
        ], { duration: 500 + Math.random() * 400, easing: 'cubic-bezier(0.1, 0.6, 0.4, 1)', fill: 'forwards' });
      }
    }, Math.max(0, 2680 - t0));
  };
  // The home page's stroke animation runs on a delay from the stylesheet; its start time lets the
  // brush fall into step with it, whichever brush runs.
  window.CCT.strokeStart = function () {
    try { var a = ink && ink.getAnimations ? ink.getAnimations()[0] : null; return (a && a.currentTime !== null) ? a.currentTime : 0; } catch (e) { return 0; }
  };
  if (brush && !document.getElementById('brush-gl')) { window.CCT.startFlatBrush(); }
})();
