<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('password','password-confirm') displayInfo=false; section>
  <#if section = "header">
    ${msg("updatePasswordTitle")}
  <#elseif section = "form">
    <form id="kc-passwd-update-form" class="${properties.kcFormClass!}" action="${url.loginAction}" method="post">
      <input type="text" id="username" name="username" value="${username}" autocomplete="username"
             readonly="readonly" style="display:none;" />
      <input type="password" id="password" name="password" autocomplete="current-password"
             style="display:none;" />

      <#-- BSI-Passwortrichtlinie-Hinweisbox -->
      <div class="bsi-policy-info">
        <strong>Passwortanforderungen (BSI IT-Grundschutz)</strong>
        <ul>
          <li>Mindestens <strong>12 Zeichen</strong></li>
          <li>Mindestens 1 <strong>Großbuchstabe</strong> (A–Z)</li>
          <li>Mindestens 1 <strong>Kleinbuchstabe</strong> (a–z)</li>
          <li>Mindestens 1 <strong>Ziffer</strong> (0–9)</li>
          <li>Mindestens 1 <strong>Sonderzeichen</strong> (z.&nbsp;B. !@#$%)</li>
          <li>Nicht identisch mit Benutzername oder E-Mail</li>
          <li>Keine der letzten 5 verwendeten Passwörter</li>
        </ul>
      </div>

      <div class="${properties.kcFormGroupClass!}">
        <div class="${properties.kcLabelWrapperClass!}">
          <label for="password-new" class="${properties.kcLabelClass!}">${msg("newPassword")}</label>
        </div>
        <div class="${properties.kcInputWrapperClass!}">
          <div class="${properties.kcInputGroup!}" dir="ltr">
            <input type="password" id="password-new" name="password-new"
                   class="${properties.kcInputClass!}"
                   autofocus autocomplete="new-password"
                   aria-invalid="<#if messagesPerField.existsError('password','password-confirm')>true</#if>"
            />
            <#if passwordVisible??>
              <button class="${properties.kcFormPasswordVisibilityButtonClass!}" type="button"
                      aria-label="${msg('showPassword')}"
                      aria-controls="password-new" data-label-show="${msg('showPassword')}"
                      data-label-hide="${msg('hidePassword')}">
                <span class="${properties.kcFormPasswordVisibilityIconShow!}" aria-hidden="true"></span>
                <span class="${properties.kcFormPasswordVisibilityIconHide!}" aria-hidden="true"></span>
              </button>
            </#if>
          </div>
          <#if messagesPerField.existsError('password')>
            <span id="input-error-password" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">
              ${kcSanitize(messagesPerField.get('password'))?no_esc}
            </span>
          </#if>
        </div>
      </div>

      <div class="${properties.kcFormGroupClass!}">
        <div class="${properties.kcLabelWrapperClass!}">
          <label for="password-confirm" class="${properties.kcLabelClass!}">${msg("passwordConfirm")}</label>
        </div>
        <div class="${properties.kcInputWrapperClass!}">
          <div class="${properties.kcInputGroup!}" dir="ltr">
            <input type="password" id="password-confirm" name="password-confirm"
                   class="${properties.kcInputClass!}"
                   autocomplete="new-password"
                   aria-invalid="<#if messagesPerField.existsError('password-confirm')>true</#if>"
            />
            <#if passwordVisible??>
              <button class="${properties.kcFormPasswordVisibilityButtonClass!}" type="button"
                      aria-label="${msg('showPasswordConfirm')}"
                      aria-controls="password-confirm" data-label-show="${msg('showPassword')}"
                      data-label-hide="${msg('hidePassword')}">
                <span class="${properties.kcFormPasswordVisibilityIconShow!}" aria-hidden="true"></span>
                <span class="${properties.kcFormPasswordVisibilityIconHide!}" aria-hidden="true"></span>
              </button>
            </#if>
          </div>
          <#if messagesPerField.existsError('password-confirm')>
            <span id="input-error-password-confirm" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">
              ${kcSanitize(messagesPerField.get('password-confirm'))?no_esc}
            </span>
          </#if>
        </div>
      </div>

      <div class="${properties.kcFormGroupClass!}">
        <#if isAppInitiatedAction??>
          <input class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonLargeClass!}"
                 type="submit" value="${msg("doSubmit")}" />
          <button class="${properties.kcButtonClass!} ${properties.kcButtonDefaultClass!} ${properties.kcButtonLargeClass!}"
                  type="submit" name="cancel-aia" value="true">${msg("doCancel")}</button>
        <#else>
          <input class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonBlockClass!} ${properties.kcButtonLargeClass!}"
                 type="submit" value="${msg("doSubmit")}" />
        </#if>
      </div>
    </form>
  </#if>
</@layout.registrationLayout>
